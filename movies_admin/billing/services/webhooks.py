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


def _extract_refund_id(event_type: str, obj: dict) -> str | None:
    if event_type == "refund.updated" and obj.get("id"):
        return obj.get("id")
    if event_type == "charge.refunded":
        refunds = obj.get("refunds", {}).get("data", [])
        if refunds:
            return refunds[0].get("id")
    return None


def process_stripe_event(
    *, event: dict, raw_payload: bytes
) -> tuple[WebhookEvent, bool]:
    event_id = event.get("id")
    event_type = event.get("type", "unknown")
    payload_hash = hashlib.sha256(raw_payload).hexdigest()

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

    obj = event.get("data", {}).get("object", {})

    if event_type in {"payment_intent.succeeded", "payment_intent.payment_failed"}:
        payment_intent_id = obj.get("id")
        payment = Payment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()
        if payment:
            payment.status = (
                PaymentStatus.SUCCEEDED
                if event_type == "payment_intent.succeeded"
                else PaymentStatus.FAILED
            )
            payment.save(update_fields=["status", "updated_at"])

    if event_type in {"charge.refunded", "refund.updated"}:
        refund_id = _extract_refund_id(event_type, obj)
        if refund_id:
            refund = Refund.objects.filter(stripe_refund_id=refund_id).first()
            if refund:
                if event_type == "charge.refunded" or obj.get("status") == "succeeded":
                    refund.status = RefundStatus.SUCCEEDED
                elif obj.get("status") in {"failed", "canceled"}:
                    refund.status = RefundStatus.FAILED
                refund.save(update_fields=["status", "updated_at"])

    webhook_event.status = WebhookEventStatus.PROCESSED
    webhook_event.processed_at = datetime.now(tz=UTC)
    webhook_event.save(update_fields=["status", "processed_at"])
    return webhook_event, True
