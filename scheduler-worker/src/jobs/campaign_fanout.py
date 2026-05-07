"""Queued campaign fan-out job.

This job is intentionally isolated from API workers:
- API only marks campaigns as QUEUED.
- scheduler-worker periodically picks QUEUED campaigns from DB.
- selected campaign row is locked with FOR UPDATE SKIP LOCKED for safe horizontal scaling.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from aiokafka import AIOKafkaProducer
from sqlalchemy import text

from src.core.config import settings
from src.core.db import async_session
from src.services.api_clients import iter_user_ids

logger = logging.getLogger(__name__)

DELIVERY_TOPIC = "notifications.delivery"


async def run_queued_campaigns() -> None:
    """Entry point for periodic queued-campaign processing."""
    producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await producer.start()
    processed = 0
    try:
        for _ in range(settings.campaign_fanout_batch_size):
            handled = await _process_one_campaign(producer)
            if not handled:
                break
            processed += 1
    finally:
        await producer.stop()

    if processed:
        logger.info("campaign_fanout: processed %d campaign(s)", processed)


async def _process_one_campaign(producer: AIOKafkaProducer) -> bool:
    """Process one QUEUED campaign, returning True when one was handled."""
    async with async_session() as session:
        campaign = await _claim_next_queued_campaign(session)
        if campaign is None:
            await session.rollback()
            return False

        campaign_id = campaign["id"]
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        template_id = campaign["template_id"]
        if isinstance(template_id, str):
            template_id = uuid.UUID(template_id)

        template_variables: dict[str, Any] = campaign["template_variables"] or {}

        try:
            published = await _publish_campaign_messages(
                producer=producer,
                campaign_id=campaign_id,
                template_id=template_id,
                template_variables=template_variables,
            )
            logger.info(
                "campaign_fanout: campaign %s published %d messages",
                campaign_id,
                published,
            )
            await _mark_campaign_done(session, campaign_id)
            await session.commit()
        except Exception:
            # Rollback preserves QUEUED status; worker can retry in next poll cycle.
            await session.rollback()
            logger.exception(
                "campaign_fanout: processing failed for campaign %s; will retry",
                campaign_id,
            )
            return False
        else:
            return True


async def _claim_next_queued_campaign(session) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT id, template_id, template_variables
            FROM notif.campaigns
            WHERE status = 'QUEUED'
            ORDER BY triggered_at NULLS FIRST, created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
    )
    return result.mappings().first()


async def _mark_campaign_done(session, campaign_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            UPDATE notif.campaigns
            SET status = 'DONE', completed_at = :completed_at
            WHERE id = :campaign_id
            """
        ),
        {"campaign_id": campaign_id, "completed_at": datetime.now(UTC)},
    )


async def _publish_campaign_messages(
    producer: AIOKafkaProducer,
    campaign_id: uuid.UUID,
    template_id: uuid.UUID,
    template_variables: dict[str, Any],
) -> int:
    published = 0
    async for user_id in iter_user_ids():
        idempotency_key = f"campaign:{campaign_id}:user:{user_id}"
        message = {
            "campaign_id": str(campaign_id),
            "user_id": user_id,
            "template_id": str(template_id),
            "template_variables": template_variables,
            "channel": "EMAIL",
            "idempotency_key": idempotency_key,
        }
        await producer.send(
            DELIVERY_TOPIC,
            key=idempotency_key.encode(),
            value=json.dumps(message).encode(),
        )
        published += 1
    return published
