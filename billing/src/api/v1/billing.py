from typing import Annotated
from uuid import UUID

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_user_id_header
from src.core.config import settings
from src.db.postgres import get_session
from src.models.billing import Payment
from src.schemas.billing import (
    PaymentCreateRequest,
    PaymentResponse,
    RefundCreateRequest,
    RefundResponse,
    WebhookResponse,
)
from src.services.errors import BillingValidationError
from src.services.payments import create_payment_intent_for_user
from src.services.refunds import create_refund_for_payment
from src.services.webhooks import process_stripe_event

router = APIRouter(redirect_slashes=False)

type UserIdDep = Annotated[UUID, Depends(get_user_id_header)]
type SessionDep = Annotated[AsyncSession, Depends(get_session)]
type StripeSignatureHeader = Annotated[
    str | None,
    Header(alias="Stripe-Signature"),
]


@router.post("/payments/create", response_model=PaymentResponse)
async def create_payment(
    payload: PaymentCreateRequest,
    user_id: UserIdDep,
    session: SessionDep,
) -> PaymentResponse:
    try:
        result = await create_payment_intent_for_user(
            session,
            user_id=user_id,
            operation_id=payload.operation_id,
            amount=payload.amount,
            currency=payload.currency,
        )
    except BillingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PaymentResponse(
        id=result.payment.id,
        operation_id=result.payment.operation_id,
        status=result.payment.status,
        amount=result.payment.amount,
        currency=result.payment.currency,
        stripe_payment_intent_id=result.payment.stripe_payment_intent_id,
        client_secret=result.client_secret,
        created=result.created,
        created_at=result.payment.created_at,
        updated_at=result.payment.updated_at,
    )


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    user_id: UserIdDep,
    session: SessionDep,
) -> PaymentResponse:
    payment = await session.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found.")

    return PaymentResponse(
        id=payment.id,
        operation_id=payment.operation_id,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        stripe_payment_intent_id=payment.stripe_payment_intent_id,
        client_secret=None,
        created=False,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


@router.post("/refunds/create", response_model=RefundResponse)
async def create_refund(
    payload: RefundCreateRequest,
    user_id: UserIdDep,
    session: SessionDep,
) -> RefundResponse:
    try:
        result = await create_refund_for_payment(
            session,
            user_id=user_id,
            payment_id=payload.payment_id,
            operation_id=payload.operation_id,
            amount=payload.amount,
            reason=payload.reason,
        )
    except BillingValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RefundResponse(
        id=result.refund.id,
        payment_id=result.refund.payment_id,
        operation_id=result.refund.operation_id,
        status=result.refund.status,
        amount=result.refund.amount,
        currency=result.refund.currency,
        reason=result.refund.reason,
        stripe_refund_id=result.refund.stripe_refund_id,
        created=result.created,
        created_at=result.refund.created_at,
        updated_at=result.refund.updated_at,
    )


@router.post("/webhooks/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    session: SessionDep,
    stripe_signature: StripeSignatureHeader = None,
) -> WebhookResponse:
    if not stripe_signature:
        raise HTTPException(
            status_code=400, detail="Stripe-Signature header is required."
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid Stripe webhook payload."
        ) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=400, detail="Invalid Stripe signature."
        ) from exc

    result = await process_stripe_event(session, event=event, raw_payload=payload)
    return WebhookResponse(
        webhook_event_id=result.webhook_event.id,
        created=result.created,
        status=result.webhook_event.status,
    )
