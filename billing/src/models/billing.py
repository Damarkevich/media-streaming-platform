from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.postgres import Base


class PaymentStatus(StrEnum):
    NEW = "new"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class RefundStatus(StrEnum):
    NEW = "new"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class WebhookEventStatus(StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"


class BillingProfile(Base):
    __tablename__ = "billing_profiles"
    __table_args__ = (UniqueConstraint("user_id", name="uq_billing_profiles_user_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    operation_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PaymentStatus.NEW.value
    )
    amount: Mapped[int] = mapped_column(nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="rub")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    refunds: Mapped[list[Refund]] = relationship(
        "Refund", back_populates="payment", lazy="selectin"
    )


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    operation_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=RefundStatus.NEW.value
    )
    amount: Mapped[int] = mapped_column(nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="rub")
    reason: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    stripe_refund_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    payment: Mapped[Payment] = relationship("Payment", back_populates="refunds")


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stripe_event_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=WebhookEventStatus.PENDING.value
    )
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str] = mapped_column(nullable=False, default="")
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
