from __future__ import annotations

from dataclasses import dataclass

import stripe
from django.db import transaction

from billing.models import Payment, PaymentStatus
from billing.services.customers import create_or_get_customer_for_user
from billing.services.errors import BillingValidationError
from billing.services.stripe_client import configure_stripe_client


@dataclass(slots=True)
class PaymentCreateResult:
    payment: Payment
    created: bool
    client_secret: str | None = None


def create_payment_intent_for_user(
    user,
    *,
    operation_id: str,
    amount: int,
    currency: str = "rub",
) -> PaymentCreateResult:
    if amount < 1:
        msg = "Amount must be greater than zero in minor units."
        raise BillingValidationError(msg)

    profile, _ = create_or_get_customer_for_user(user, operation_id=operation_id)
    configure_stripe_client()

    with transaction.atomic():
        payment, created = Payment.objects.get_or_create(
            operation_id=operation_id,
            defaults={
                "user": user,
                "amount": amount,
                "currency": currency,
                "status": PaymentStatus.PENDING,
                "stripe_customer_id": profile.stripe_customer_id,
            },
        )

        payment = Payment.objects.select_for_update().get(pk=payment.pk)

        if payment.user.pk != user.pk:
            msg = "Operation ID already exists for another user."
            raise BillingValidationError(msg)
        if payment.amount != amount or payment.currency != currency:
            msg = "Operation ID already exists with different amount or currency."
            raise BillingValidationError(msg)
        if payment.stripe_payment_intent_id:
            return PaymentCreateResult(
                payment=payment,
                created=False,
                client_secret=None,
            )

        payment_amount = payment.amount
        payment_currency = payment.currency

        idempotency_key = f"payment-create:{operation_id}"
        payment_intent = stripe.PaymentIntent.create(
            amount=payment_amount,
            currency=payment_currency,
            customer=profile.stripe_customer_id,
            metadata={"user_id": str(user.pk), "payment_id": str(payment.pk)},
            automatic_payment_methods={"enabled": True},
            idempotency_key=idempotency_key,
        )

        payment.status = PaymentStatus.PENDING
        payment.stripe_payment_intent_id = getattr(
            payment_intent, "id", None
        ) or payment_intent.get("id")
        payment.save(update_fields=["status", "stripe_payment_intent_id", "updated_at"])

        client_secret = getattr(
            payment_intent, "client_secret", None
        ) or payment_intent.get("client_secret")

        return PaymentCreateResult(
            payment=payment,
            created=created,
            client_secret=client_secret,
        )
