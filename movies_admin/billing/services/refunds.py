from __future__ import annotations

from dataclasses import dataclass

import stripe
from django.db import transaction

from billing.models import Payment, Refund, RefundStatus
from billing.services.stripe_client import configure_stripe_client


@dataclass(slots=True)
class RefundCreateResult:
    refund: Refund
    created: bool


def create_refund_for_payment(
    *,
    payment: Payment,
    operation_id: str,
    amount: int | None = None,
    reason: str = "",
) -> RefundCreateResult:
    configure_stripe_client()

    refund_amount = amount or payment.amount

    with transaction.atomic():
        refund, created = Refund.objects.get_or_create(
            operation_id=operation_id,
            defaults={
                "payment": payment,
                "status": RefundStatus.PENDING,
                "amount": refund_amount,
                "currency": payment.currency,
                "reason": reason,
            },
        )
        if not created:
            return RefundCreateResult(refund=refund, created=False)

    stripe_refund = stripe.Refund.create(
        payment_intent=payment.stripe_payment_intent_id,
        amount=refund.amount,
        reason="requested_by_customer" if reason else None,
        metadata={
            "payment_id": str(payment.pk),
            "refund_id": str(refund.pk),
            "operation_id": operation_id,
        },
        idempotency_key=f"refund-create:{operation_id}",
    )

    refund.stripe_refund_id = getattr(stripe_refund, "id", None) or stripe_refund.get(
        "id"
    )
    refund.status = RefundStatus.PENDING
    refund.save(update_fields=["stripe_refund_id", "status", "updated_at"])
    return RefundCreateResult(refund=refund, created=True)
