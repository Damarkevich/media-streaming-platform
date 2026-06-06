from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio
import stripe
from sqlalchemy import func, select

from src.models.billing import Payment, PaymentStatus, Refund, RefundStatus
from src.services.errors import BillingValidationError
from src.services.stripe_client import configure_stripe_client

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RefundCreateResult:
    refund: Refund
    created: bool


async def _create_stripe_refund(**kwargs):
    return await anyio.to_thread.run_sync(lambda: stripe.Refund.create(**kwargs))


def _validate_payment_for_refund(
    payment: Payment | None,
    *,
    amount: int | None,
) -> int:
    if payment is None:
        msg = "Payment not found for current user."
        raise BillingValidationError(msg)

    if payment.status != PaymentStatus.SUCCEEDED.value:
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

    return refund_amount


async def _get_or_create_refund(
    session: AsyncSession,
    *,
    payment: Payment,
    operation_id: str,
    refund_amount: int,
    reason: str,
) -> RefundCreateResult:
    existing_refund = await session.scalar(
        select(Refund)
        .where(Refund.operation_id == operation_id)
        .with_for_update(of=Refund)
    )
    if existing_refund is not None:
        if existing_refund.payment_id != payment.id:
            msg = "Operation ID already exists for another payment."
            raise BillingValidationError(msg)
        return RefundCreateResult(refund=existing_refund, created=False)

    reserved_amount = await session.scalar(
        select(func.coalesce(func.sum(Refund.amount), 0)).where(
            Refund.payment_id == payment.id,
            Refund.status.in_(
                [
                    RefundStatus.NEW.value,
                    RefundStatus.PENDING.value,
                    RefundStatus.SUCCEEDED.value,
                ]
            ),
        )
    )
    available_amount = payment.amount - int(reserved_amount or 0)
    if refund_amount > available_amount:
        msg = "Refund amount exceeds available refundable amount."
        raise BillingValidationError(msg)

    refund = Refund(
        payment_id=payment.id,
        operation_id=operation_id,
        status=RefundStatus.NEW.value,
        amount=refund_amount,
        currency=payment.currency,
        reason=reason,
    )
    session.add(refund)
    await session.flush()
    return RefundCreateResult(refund=refund, created=True)


def _build_refund_metadata(payment: Payment, refund: Refund, operation_id: str) -> dict:
    return {
        "payment_id": str(payment.id),
        "refund_id": str(refund.id),
        "operation_id": operation_id,
    }


async def _mark_refund_failed(
    session: AsyncSession,
    *,
    refund_id,
    exc: Exception,
) -> None:
    async with session.begin():
        locked_refund = await session.scalar(
            select(Refund).where(Refund.id == refund_id).with_for_update(of=Refund)
        )
        metadata = dict(locked_refund.metadata_json)
        metadata["stripe_error"] = str(exc)
        locked_refund.metadata_json = metadata
        locked_refund.status = RefundStatus.FAILED.value
        await session.flush()


async def _finalize_refund_pending(
    session: AsyncSession,
    *,
    refund_id,
    stripe_refund_id: str,
    created: bool,
) -> RefundCreateResult:
    async with session.begin():
        locked_refund = await session.scalar(
            select(Refund).where(Refund.id == refund_id).with_for_update(of=Refund)
        )
        locked_refund.stripe_refund_id = stripe_refund_id
        locked_refund.status = RefundStatus.PENDING.value
        await session.flush()
        return RefundCreateResult(refund=locked_refund, created=created)


async def create_refund_for_payment(
    session: AsyncSession,
    *,
    user_id: UUID,
    payment_id: UUID,
    operation_id: str,
    amount: int | None = None,
    reason: str = "",
) -> RefundCreateResult:
    configure_stripe_client()

    async with session.begin():
        payment = await session.scalar(
            select(Payment)
            .where(Payment.id == payment_id, Payment.user_id == user_id)
            .with_for_update(of=Payment)
        )
        refund_amount = _validate_payment_for_refund(payment, amount=amount)
        draft = await _get_or_create_refund(
            session,
            payment=payment,
            operation_id=operation_id,
            refund_amount=refund_amount,
            reason=reason,
        )
        if draft.refund.stripe_refund_id:
            return RefundCreateResult(refund=draft.refund, created=False)

        if not draft.created:
            logger.info(
                "Recovering incomplete refund create after previous partial failure",
                extra={"operation_id": operation_id, "refund_id": str(draft.refund.id)},
            )

    logger.info(
        "Creating Stripe Refund",
        extra={
            "operation_id": operation_id,
            "payment_id": str(payment_id),
            "refund_id": str(draft.refund.id),
            "amount": draft.refund.amount,
        },
    )
    stripe_kwargs: dict = {
        "payment_intent": payment.stripe_payment_intent_id,
        "amount": draft.refund.amount,
        "metadata": _build_refund_metadata(payment, draft.refund, operation_id),
        "idempotency_key": f"refund-create:{operation_id}",
    }
    if reason:
        stripe_kwargs["reason"] = "requested_by_customer"

    try:
        stripe_refund = await _create_stripe_refund(**stripe_kwargs)
    except stripe.error.StripeError as exc:
        logger.error(
            "Stripe refund creation failed",
            extra={"operation_id": operation_id, "refund_id": str(draft.refund.id)},
            exc_info=True,
        )
        await _mark_refund_failed(session, refund_id=draft.refund.id, exc=exc)
        msg = "Stripe is temporarily unavailable for refund creation. Please retry."
        raise BillingValidationError(msg) from exc

    stripe_refund_id = (
        stripe_refund.get("id") if isinstance(stripe_refund, dict) else stripe_refund.id
    )
    logger.info(
        "Stripe Refund created, pending webhook confirmation",
        extra={
            "operation_id": operation_id,
            "refund_id": str(draft.refund.id),
            "stripe_refund_id": stripe_refund_id,
        },
    )
    return await _finalize_refund_pending(
        session,
        refund_id=draft.refund.id,
        stripe_refund_id=stripe_refund_id,
        created=draft.created,
    )
