"""Helpers for reserving/finalizing idempotent deliveries."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.db import async_session
from src.services import delivery_record


async def reserve_key(
    *,
    campaign_id: str | None,
    user_id: str,
    channel: str,
    idempotency_key: str,
    session: AsyncSession | None = None,
) -> bool:
    """Reserve idempotency key with optional external session."""
    if session is not None:
        return await delivery_record.reserve_delivery(
            session,
            campaign_id=campaign_id,
            user_id=user_id,
            channel=channel,
            idempotency_key=idempotency_key,
        )

    async with async_session() as own_session:
        return await delivery_record.reserve_delivery(
            own_session,
            campaign_id=campaign_id,
            user_id=user_id,
            channel=channel,
            idempotency_key=idempotency_key,
        )


async def finalize_key(
    *,
    idempotency_key: str,
    status: str,
    sent_at: datetime | None = None,
    error: str | None = None,
    session: AsyncSession | None = None,
) -> None:
    """Finalize idempotency record with optional external session."""
    if session is not None:
        await delivery_record.finalize_delivery(
            session,
            idempotency_key=idempotency_key,
            status=status,
            sent_at=sent_at,
            error=error,
        )
        return

    async with async_session() as own_session:
        await delivery_record.finalize_delivery(
            own_session,
            idempotency_key=idempotency_key,
            status=status,
            sent_at=sent_at,
            error=error,
        )
