import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user_id, require_admin
from src.db.postgres import get_session
from src.schemas.campaigns import CampaignCreate, CampaignResponse
from src.services import campaigns as svc

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CampaignResponse]:
    return await svc.get_all_campaigns(session)  # type: ignore[return-value]


@router.post(
    "/",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    data: CampaignCreate,
    created_by: Annotated[uuid.UUID, Depends(get_current_user_id)],
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    return await svc.create_campaign(session, data, created_by)  # type: ignore[return-value]


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CampaignResponse:
    campaign = await svc.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    return campaign  # type: ignore[return-value]


@router.post("/{campaign_id}/send", status_code=status.HTTP_202_ACCEPTED)
async def send_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ORJSONResponse:
    campaign = await svc.get_campaign(session, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
        )
    # Mark QUEUED (validates status + commits) while session is still open
    await svc.mark_queued(session, campaign)
    # Fan-out runs in the background with its own session
    background_tasks.add_task(svc.run_fanout, campaign_id)
    return ORJSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"campaign_id": str(campaign_id), "status": "queued"},
    )
