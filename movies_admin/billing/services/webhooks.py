from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from billing.models import (
    Payment,
    PaymentStatus,
    Refund,
    RefundStatus,
    WebhookEvent,
    WebhookEventStatus,
)


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


def _apply_payment_event(event_type: str, obj: dict) -> tuple[str, str]:
    payment_intent_id = obj.get("id")
    payment = Payment.objects.filter(stripe_payment_intent_id=payment_intent_id).first()
    if not payment:
        msg = "Payment not found for Stripe PaymentIntent event."
        return WebhookEventStatus.IGNORED, msg

    if event_type == "payment_intent.succeeded":
        if payment.status != PaymentStatus.SUCCEEDED:
            payment.status = PaymentStatus.SUCCEEDED
            payment.save(update_fields=["status", "updated_at"])
        return WebhookEventStatus.PROCESSED, ""

    if payment.status in {PaymentStatus.NEW, PaymentStatus.PENDING}:
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "updated_at"])
    return WebhookEventStatus.PROCESSED, ""


def _apply_refund_event(event_type: str, obj: dict) -> tuple[str, str]:
    refund_id = _extract_refund_id(event_type, obj)
    if not refund_id:
        msg = "Refund ID not found in Stripe refund event payload."
        return WebhookEventStatus.IGNORED, msg

    refund = Refund.objects.filter(stripe_refund_id=refund_id).first()
    if not refund:
        msg = "Refund not found for Stripe refund event."
        return WebhookEventStatus.IGNORED, msg

    if event_type == "charge.refunded" or obj.get("status") == "succeeded":
        refund.status = RefundStatus.SUCCEEDED
        refund.save(update_fields=["status", "updated_at"])
        return WebhookEventStatus.PROCESSED, ""

    if obj.get("status") in {"failed", "canceled"}:
        if refund.status != RefundStatus.SUCCEEDED:
            refund.status = RefundStatus.FAILED
            refund.save(update_fields=["status", "updated_at"])
        return WebhookEventStatus.PROCESSED, ""

    msg = "Unsupported Stripe refund status in refund.updated event."
    return WebhookEventStatus.IGNORED, msg


def _save_webhook_event_result(
    webhook_event: WebhookEvent, webhook_status: str, error_message: str
) -> None:
    webhook_event.status = webhook_status
    webhook_event.error_message = error_message
    webhook_event.processed_at = datetime.now(tz=UTC)
    webhook_event.save(update_fields=["status", "error_message", "processed_at"])


def process_stripe_event(
    *, event: dict, raw_payload: bytes
) -> tuple[WebhookEvent, bool]:
    event_type = event.get("type", "unknown")
    payload_hash = hashlib.sha256(raw_payload).hexdigest()
    event_id = _resolve_event_id(event, payload_hash)

    webhook_event, created = WebhookEvent.objects.get_or_create(
        stripe_event_id=event_id,
        defaults={
            "event_type": event_type,
            "status": WebhookEventStatus.PENDING,
            "payload_hash": payload_hash,
            "payload": event,
        },
    )
    if not created:
        return webhook_event, False

    obj = _extract_object(event)

    if event_type in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
        webhook_status, error_message = _apply_payment_event(event_type, obj)
    elif event_type in {"charge.refunded", "refund.updated"}:
        webhook_status, error_message = _apply_refund_event(event_type, obj)
    else:
        webhook_status = WebhookEventStatus.IGNORED
        error_message = "Unsupported Stripe event type."

    _save_webhook_event_result(webhook_event, webhook_status, error_message)
    return webhook_event, True
