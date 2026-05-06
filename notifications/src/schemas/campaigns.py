import uuid
from datetime import datetime

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str
    campaign_type: str = "INSTANT"
    template_id: uuid.UUID
    template_variables: dict = {}
    audience: str = "ALL_USERS"
    description: str | None = None


class CampaignResponse(BaseModel):
    id: uuid.UUID
    name: str
    campaign_type: str
    template_id: uuid.UUID
    template_variables: dict
    audience: str
    status: str
    description: str | None
    created_by: uuid.UUID | None
    created_at: datetime
    triggered_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
