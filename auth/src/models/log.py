import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.postgres import Base


class LogType(StrEnum):
    """Supported audit log event types."""

    LOGIN = "login"
    API_LOGIN = "api_login"


class Log(Base):
    """Audit log record for user actions."""

    __tablename__ = "logs"
    __table_args__ = (
        Index("ix_auth_logs_user_id_created_at", "user_id", "created_at"),
        {"schema": "auth"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=False,
    )
    log_type: Mapped[LogType] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    def __init__(self, user_id: uuid.UUID, log_type: LogType) -> None:
        self.user_id = user_id
        self.log_type = log_type

    def __repr__(self) -> str:
        return f"<Log {self.log_type} for user {self.user_id} at {self.created_at.isoformat()}>"
