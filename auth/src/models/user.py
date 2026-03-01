import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from src.db.postgres import Base
from src.models.role import UserRole

if TYPE_CHECKING:
    from src.models.role import Role


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "auth"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    login: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
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

    def __init__(self, login: str, password: str, first_name: str, last_name: str):
        self.login = login
        self.set_password(password)
        self.first_name = first_name
        self.last_name = last_name

    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    def set_password(self, password: str) -> None:
        self.password = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(str(self.password), password)

    def __repr__(self):
        return f"<User {self.login}>"
