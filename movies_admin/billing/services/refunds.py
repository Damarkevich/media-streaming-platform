from __future__ import annotations

from dataclasses import dataclass

import stripe
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce

from billing.models import Payment, PaymentStatus, Refund, RefundStatus
from billing.services.errors import BillingValidationError
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

    if payment.status != PaymentStatus.SUCCEEDED:
        msg = "Refund can be created only for succeeded payments."
        raise BillingValidationError(msg)

    if not payment.stripe_payment_intent_id:
        msg = "Payment has no Stripe PaymentIntent ID for refund creation."
        raise BillingValidationError(msg)

    if amount is not None and amount < 1:
        msg = "Refund amount must be greater than zero in minor units."
        raise BillingValidationError(msg)

    refund_amount = amount or payment.amount
    if refund_amount > payment.amount:
        msg = "Refund amount cannot exceed the original payment amount."
        raise BillingValidationError(msg)

    with transaction.atomic():
        existing_refund = (
            Refund.objects.select_for_update().filter(operation_id=operation_id).first()
        )
        if existing_refund is not None:
            return RefundCreateResult(refund=existing_refund, created=False)

        locked_payment = Payment.objects.select_for_update().get(pk=payment.pk)
        reserved_amount = (
            Refund.objects.filter(
                payment=locked_payment,
                status__in=(
                    RefundStatus.NEW,
                    RefundStatus.PENDING,
                    RefundStatus.SUCCEEDED,
                ),
            ).aggregate(total=Coalesce(Sum("amount"), 0))["total"]
            or 0
        )
        available_amount = locked_payment.amount - reserved_amount
        if refund_amount > available_amount:
            msg = "Refund amount exceeds available refundable amount."
            raise BillingValidationError(msg)

        refund = Refund.objects.create(
            payment=locked_payment,
            operation_id=operation_id,
            status=RefundStatus.PENDING,
            amount=refund_amount,
            currency=locked_payment.currency,
            reason=reason,
        )

    stripe_refund = stripe.Refund.create(
        payment_intent=locked_payment.stripe_payment_intent_id,
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
