import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.postgres import Base

SCHEMA = "notif"


class Delivery(Base):
    """Per-user delivery record — idempotent log of every send attempt."""

    __tablename__ = "deliveries"
    __table_args__ = {"schema": SCHEMA}  # noqa: RUF012

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # nullable — event-triggered deliveries have no explicit campaign
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    # EMAIL (only channel for MVP)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="EMAIL")
    # Unique key prevents double-delivery.
    # Format: "campaign:{campaign_id}:user:{user_id}"
    #      or "review_liked:{review_id}:{user_id}"
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    # PENDING | SENT | FAILED | THROTTLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Delivery user={self.user_id!r} status={self.status!r}>"
