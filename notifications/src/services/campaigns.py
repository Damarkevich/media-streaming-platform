import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.campaign import Campaign
from src.schemas.campaigns import CampaignCreate


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
    """Mark campaign QUEUED; scheduler-worker picks it up and performs fan-out."""
    if campaign.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot trigger campaign with status '{campaign.status}'",
        )
    campaign.status = "QUEUED"
    campaign.triggered_at = datetime.now(UTC)
    await session.commit()
