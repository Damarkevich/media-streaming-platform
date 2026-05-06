import uuid
from datetime import datetime

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    notification_type: str
    subject_template: str
    body_template: str
    required_variables: list[str] = []


class TemplateUpdate(BaseModel):
    name: str | None = None
    notification_type: str | None = None
    subject_template: str | None = None
    body_template: str | None = None
    required_variables: list[str] | None = None


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    notification_type: str
    subject_template: str
    body_template: str
    required_variables: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
