from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import uuid4

import stripe
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from src.models.billing import BillingProfile
from src.services.stripe_client import configure_stripe_client

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def create_or_get_customer_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    operation_id: str | None = None,
) -> tuple[BillingProfile, bool]:
    configure_stripe_client()

    await session.execute(
        insert(BillingProfile)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )

    profile = await session.scalar(
        select(BillingProfile)
        .where(BillingProfile.user_id == user_id)
        .with_for_update(of=BillingProfile)
    )
    if profile is None:
        msg = "Failed to resolve billing profile race condition."
        raise RuntimeError(msg)

    if profile.stripe_customer_id:
        logger.debug("Billing profile resolved", extra={"user_id": str(user_id)})
        return profile, False

    logger.info("Creating Stripe customer", extra={"user_id": str(user_id)})
    idempotency_key = f"customer-create:{user_id}:{operation_id or uuid4()}"
    customer = stripe.Customer.create(
        metadata={"user_id": str(user_id)},
        idempotency_key=idempotency_key,
    )
    customer_id = customer.get("id") if isinstance(customer, dict) else customer.id

    if not customer_id:
        msg = "Stripe did not return customer id"
        raise RuntimeError(msg)

    logger.info(
        "Stripe customer created",
        extra={"user_id": str(user_id), "stripe_customer_id": customer_id},
    )
    profile.stripe_customer_id = customer_id
    await session.flush()
    return profile, True
