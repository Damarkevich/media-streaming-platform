import json
import logging
import uuid
from datetime import UTC, datetime

import httpx
from aiokafka import AIOKafkaProducer
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.db.postgres import async_session
from src.models.campaign import Campaign
from src.schemas.campaigns import CampaignCreate

logger = logging.getLogger(__name__)

DELIVERY_TOPIC = "notifications.delivery"


async def get_all_campaigns(session: AsyncSession) -> list[Campaign]:
    result = await session.execute(select(Campaign))
    return list(result.scalars().all())


async def get_campaign(
    session: AsyncSession, campaign_id: uuid.UUID
) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def create_campaign(
    session: AsyncSession,
    data: CampaignCreate,
    created_by: uuid.UUID,
) -> Campaign:
    campaign = Campaign(**data.model_dump(), created_by=created_by)
    session.add(campaign)
    await session.commit()
    await session.refresh(campaign)
    return campaign


async def mark_queued(session: AsyncSession, campaign: Campaign) -> None:
    """Mark campaign QUEUED inside the request session before handing off to background."""
    if campaign.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot trigger campaign with status '{campaign.status}'",
        )
    campaign.status = "QUEUED"
    campaign.triggered_at = datetime.now(UTC)
    await session.commit()


async def run_fanout(campaign_id: uuid.UUID) -> None:
    """Background task: fetch users, publish to Kafka, mark DONE/FAILED."""
    async with async_session() as session:
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            logger.error("Campaign %s not found during fanout", campaign_id)
            return
        try:
            await _fanout(session, campaign)
        except Exception:
            logger.exception("Fanout failed for campaign %s", campaign_id)
            campaign.status = "FAILED"
            await session.commit()


async def _fanout(session: AsyncSession, campaign: Campaign) -> None:
    user_ids = await _fetch_all_user_ids()
    if not user_ids:
        logger.warning("Fanout for campaign %s: no users found", campaign.id)

    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    await producer.start()
    try:
        for user_id in user_ids:
            idempotency_key = f"campaign:{campaign.id}:user:{user_id}"
            message = {
                "campaign_id": str(campaign.id),
                "user_id": user_id,
                "template_id": str(campaign.template_id),
                "template_variables": campaign.template_variables,
                "channel": "EMAIL",
                "idempotency_key": idempotency_key,
            }
            await producer.send(
                DELIVERY_TOPIC,
                key=idempotency_key.encode(),
                value=json.dumps(message).encode(),
            )
    finally:
        await producer.stop()

    campaign.status = "DONE"
    campaign.completed_at = datetime.now(UTC)
    await session.commit()
    logger.info(
        "Fanout complete for campaign %s: %d messages published",
        campaign.id,
        len(user_ids),
    )


async def _fetch_all_user_ids() -> list[str]:
    """Paginate auth internal endpoint to collect all user IDs."""
    ids: list[str] = []
    page = 0
    page_size = 500
    async with httpx.AsyncClient() as client:
        while True:
            resp = await client.get(
                f"{settings.auth_internal_url}/api/v1/users/internal",
                params={"page": page, "page_size": page_size},
                headers={"X-Internal-Key": settings.internal_api_key},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            items: list[dict] = data.get("items", [])
            ids.extend(item["user_id"] for item in items)
            if len(items) < page_size:
                break
            page += 1
    return ids
