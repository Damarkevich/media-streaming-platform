"""Delivery record persistence — writes to notif.deliveries table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

INSERT_SQL = text("""
INSERT INTO notif.deliveries
    (id, campaign_id, user_id, channel, idempotency_key, status, sent_at, error, created_at)
VALUES
    (:id, :campaign_id, :user_id, :channel, :idempotency_key, :status, :sent_at, :error, :created_at)
ON CONFLICT (idempotency_key) DO NOTHING
""")


async def record_delivery(
    session: AsyncSession,
    *,
    campaign_id: str | None,
    user_id: str,
    channel: str,
    idempotency_key: str,
    status: str,
    sent_at: datetime | None = None,
    error: str | None = None,
) -> None:
    await session.execute(
        INSERT_SQL,
        {
            "id": str(uuid.uuid4()),
            "campaign_id": campaign_id,
            "user_id": user_id,
            "channel": channel,
            "idempotency_key": idempotency_key,
            "status": status,
            "sent_at": sent_at,
            "error": error,
            "created_at": datetime.now(UTC),
        },
    )
    await session.commit()
