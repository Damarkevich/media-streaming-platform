import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.postgres import Base

SCHEMA = "notif"


class Campaign(Base):
    """A notification campaign (instant, scheduled, or event-triggered)."""

    __tablename__ = "campaigns"
    __table_args__ = {"schema": SCHEMA}  # noqa: RUF012

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # INSTANT | SCHEDULED | EVENT_TRIGGERED
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # JSON variables to fill into the template, e.g. {"custom_message": "Hello!"}
    template_variables: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    # ALL_USERS (only audience type for MVP)
    audience: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ALL_USERS"
    )
    # DRAFT | QUEUED | RUNNING | DONE | FAILED
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Campaign name={self.name!r} status={self.status!r}>"
