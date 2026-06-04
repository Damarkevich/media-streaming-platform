from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import stripe
from sqlalchemy import select

from src.models.billing import Payment, PaymentStatus
from src.services.customers import create_or_get_customer_for_user
from src.services.errors import BillingValidationError
from src.services.stripe_client import configure_stripe_client

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PaymentCreateResult:
    payment: Payment
    created: bool
    client_secret: str | None = None


async def create_payment_intent_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    operation_id: str,
    amount: int,
    currency: str = "rub",
) -> PaymentCreateResult:
    if amount < 1:
        msg = "Amount must be greater than zero in minor units."
        raise BillingValidationError(msg)

    configure_stripe_client()

    async with session.begin():
        profile, _ = await create_or_get_customer_for_user(
            session,
            user_id=user_id,
            operation_id=operation_id,
        )

        payment = await session.scalar(
            select(Payment)
            .where(Payment.operation_id == operation_id)
            .with_for_update(of=Payment)
        )

        created = False
        if payment is None:
            payment = Payment(
                user_id=user_id,
                operation_id=operation_id,
                status=PaymentStatus.PENDING.value,
                amount=amount,
                currency=currency,
                stripe_customer_id=profile.stripe_customer_id,
            )
            session.add(payment)
            await session.flush()
            created = True

        if payment.user_id != user_id:
            msg = "Operation ID already exists for another user."
            raise BillingValidationError(msg)

        if payment.amount != amount or payment.currency != currency:
            msg = "Operation ID already exists with different amount or currency."
            raise BillingValidationError(msg)

        if payment.stripe_payment_intent_id:
            logger.info(
                "Payment already has PaymentIntent, returning idempotent result",
                extra={"operation_id": operation_id, "payment_id": str(payment.id)},
            )
            return PaymentCreateResult(
                payment=payment, created=False, client_secret=None
            )

        logger.info(
            "Creating Stripe PaymentIntent",
            extra={
                "operation_id": operation_id,
                "user_id": str(user_id),
                "amount": amount,
            },
        )
        payment_intent = stripe.PaymentIntent.create(
            amount=payment.amount,
            currency=payment.currency,
            customer=profile.stripe_customer_id,
            metadata={"user_id": str(user_id), "payment_id": str(payment.id)},
            automatic_payment_methods={"enabled": True},
            idempotency_key=f"payment-create:{operation_id}",
        )

        payment.stripe_payment_intent_id = (
            payment_intent.get("id")
            if isinstance(payment_intent, dict)
            else payment_intent.id
        )
        payment.status = PaymentStatus.PENDING.value
        await session.flush()

        client_secret = (
            payment_intent.get("client_secret")
            if isinstance(payment_intent, dict)
            else payment_intent.client_secret
        )
        logger.info(
            "PaymentIntent created",
            extra={
                "operation_id": operation_id,
                "payment_id": str(payment.id),
                "stripe_payment_intent_id": payment.stripe_payment_intent_id,
            },
        )
        return PaymentCreateResult(
            payment=payment,
            created=created,
            client_secret=client_secret,
        )
