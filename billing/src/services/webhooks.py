from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from src.models.billing import (
    Payment,
    PaymentStatus,
    Refund,
    RefundStatus,
    WebhookEvent,
    WebhookEventStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True)
class WebhookProcessResult:
    webhook_event: WebhookEvent
    created: bool


def _resolve_event_id(event: dict, payload_hash: str) -> str:
    event_id = event.get("id")
    if event_id:
        return event_id
    return f"missing-id:{payload_hash}"


def _extract_object(event: dict) -> dict:
    obj = event.get("data", {}).get("object", {})
    if isinstance(obj, dict):
        return obj
    return {}


def _extract_refund_id(event_type: str, obj: dict) -> str | None:
    if event_type == "refund.updated" and obj.get("id"):
        return obj.get("id")
    if event_type == "charge.refunded":
        refunds = obj.get("refunds", {}).get("data", [])
        if refunds:
            return refunds[0].get("id")
    return None


def _mark_ignored(webhook_event: WebhookEvent, message: str) -> None:
    webhook_event.status = WebhookEventStatus.IGNORED.value
    webhook_event.error_message = message


async def _handle_payment_event(
    session: AsyncSession,
    *,
    event_type: str,
    obj: dict,
    webhook_event: WebhookEvent,
) -> None:
    payment_intent_id = obj.get("id")
    payment = await session.scalar(
        select(Payment)
        .where(Payment.stripe_payment_intent_id == payment_intent_id)
        .with_for_update(of=Payment)
    )
    if payment is None:
        _mark_ignored(
            webhook_event, "Payment not found for Stripe PaymentIntent event."
        )
        return

    if event_type == "payment_intent.succeeded":
        if payment.status != PaymentStatus.SUCCEEDED.value:
            payment.status = PaymentStatus.SUCCEEDED.value
        webhook_event.status = WebhookEventStatus.PROCESSED.value
        return

    if payment.status in {PaymentStatus.NEW.value, PaymentStatus.PENDING.value}:
        payment.status = PaymentStatus.FAILED.value
    webhook_event.status = WebhookEventStatus.PROCESSED.value


async def _handle_refund_event(
    session: AsyncSession,
    *,
    event_type: str,
    obj: dict,
    webhook_event: WebhookEvent,
) -> None:
    refund_id = _extract_refund_id(event_type, obj)
    if not refund_id:
        _mark_ignored(
            webhook_event, "Refund ID not found in Stripe refund event payload."
        )
        return

    refund = await session.scalar(
        select(Refund)
        .where(Refund.stripe_refund_id == refund_id)
        .with_for_update(of=Refund)
    )
    if refund is None:
        _mark_ignored(webhook_event, "Refund not found for Stripe refund event.")
        return

    if event_type == "charge.refunded" or obj.get("status") == "succeeded":
        refund.status = RefundStatus.SUCCEEDED.value
        webhook_event.status = WebhookEventStatus.PROCESSED.value
        return

    if obj.get("status") in {"failed", "canceled"}:
        if refund.status != RefundStatus.SUCCEEDED.value:
            refund.status = RefundStatus.FAILED.value
        webhook_event.status = WebhookEventStatus.PROCESSED.value
        return

    _mark_ignored(
        webhook_event,
        "Unsupported Stripe refund status in refund.updated event.",
    )


async def process_stripe_event(
    session: AsyncSession,
    *,
    event: dict,
    raw_payload: bytes,
) -> WebhookProcessResult:
    event_type = event.get("type", "unknown")
    payload_hash = hashlib.sha256(raw_payload).hexdigest()
    event_id = _resolve_event_id(event, payload_hash)

    async with session.begin():
        existing = await session.scalar(
            select(WebhookEvent)
            .where(WebhookEvent.stripe_event_id == event_id)
            .with_for_update(of=WebhookEvent)
        )
        if existing is not None:
            return WebhookProcessResult(webhook_event=existing, created=False)

        webhook_event = WebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            status=WebhookEventStatus.PENDING.value,
            payload_hash=payload_hash,
            payload=event,
        )
        session.add(webhook_event)
        await session.flush()

        obj = _extract_object(event)

        if event_type in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
            await _handle_payment_event(
                session,
                event_type=event_type,
                obj=obj,
                webhook_event=webhook_event,
            )

        elif event_type in {"charge.refunded", "refund.updated"}:
            await _handle_refund_event(
                session,
                event_type=event_type,
                obj=obj,
                webhook_event=webhook_event,
            )

        else:
            _mark_ignored(webhook_event, "Unsupported Stripe event type.")

        webhook_event.processed_at = datetime.now(tz=UTC)
        await session.flush()

        return WebhookProcessResult(webhook_event=webhook_event, created=True)
