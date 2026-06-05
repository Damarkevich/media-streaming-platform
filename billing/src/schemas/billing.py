from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreateRequest(BaseModel):
    operation_id: str = Field(min_length=1, max_length=128)
    amount: int = Field(ge=1, description="Amount in minor units")
    currency: str = Field(default="rub", min_length=1, max_length=8)


class PaymentResponse(BaseModel):
    id: UUID
    operation_id: str
    status: str
    amount: int
    currency: str
    stripe_payment_intent_id: str | None
    client_secret: str | None
    created: bool
    created_at: datetime
    updated_at: datetime


class RefundCreateRequest(BaseModel):
    payment_id: UUID
    operation_id: str = Field(min_length=1, max_length=128)
    amount: int | None = Field(default=None, ge=1)
    reason: str = Field(default="", max_length=255)


class RefundResponse(BaseModel):
    id: UUID
    payment_id: UUID
    operation_id: str
    status: str
    amount: int
    currency: str
    reason: str
    stripe_refund_id: str | None
    created: bool
    created_at: datetime
    updated_at: datetime


class WebhookResponse(BaseModel):
    webhook_event_id: UUID
    created: bool
    status: str
