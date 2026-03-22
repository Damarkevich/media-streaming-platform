import asyncio
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from werkzeug.security import check_password_hash, generate_password_hash

from src.db.postgres import Base
from src.models.role import UserRole

if TYPE_CHECKING:
    from src.models.role import Role


class User(Base):
    """User account entity with credentials and RBAC links."""

    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=UserRole.__table__,
        back_populates="users",
    )
    is_superuser: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __init__(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        is_superuser: bool = False,
    ) -> None:
        if not self._is_werkzeug_password_hash(password_hash):
            raise ValueError("password_hash must be a Werkzeug password hash")
        self.email = email
        self.password = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.is_superuser = is_superuser

    @staticmethod
    def _is_werkzeug_password_hash(value: str) -> bool:
        return value.startswith(("scrypt:", "pbkdf2:"))

    @staticmethod
    def _normalize_and_validate_email(email: str) -> str:
        try:
            validated = validate_email(email, check_deliverability=False)
        except EmailNotValidError as exc:
            raise ValueError("Invalid email format") from exc
        return validated.normalized

    @classmethod
    def normalize_email(cls, email: str) -> str:
        """Normalize and validate email for all write/read paths."""
        return cls._normalize_and_validate_email(email)

    @validates("email")
    def _validate_email_assignment(self, key: str, value: str) -> str:
        return self._normalize_and_validate_email(value)

    @staticmethod
    async def hash_password(password: str) -> str:
        return await asyncio.to_thread(generate_password_hash, password)

    async def set_password(self, password: str) -> None:
        self.password = await self.hash_password(password)

    async def check_password(self, password: str) -> bool:
        return await asyncio.to_thread(check_password_hash, self.password, password)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
