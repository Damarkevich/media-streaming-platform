import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.permissions import PermissionName
from src.db.postgres import Base

if TYPE_CHECKING:
    from src.models.user import User


class RolePermission(Base):
    """Association table mapping roles to permissions."""

    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "auth"}  # noqa: RUF012

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.permissions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )


class UserRole(Base):
    """Association table mapping users to roles."""

    __tablename__ = "user_roles"
    __table_args__ = {"schema": "auth"}  # noqa: RUF012

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.roles.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        nullable=False,
    )


class Permission(Base):
    """Permission entity that can be assigned to roles."""

    __tablename__ = "permissions"
    __table_args__ = {"schema": "auth"}  # noqa: RUF012

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[PermissionName] = mapped_column(
        String(50), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )

    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary="auth.role_permissions",
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.name}>"


class Role(Base):
    """Role entity grouping permissions and users."""

    __tablename__ = "roles"
    __table_args__ = {"schema": "auth"}  # noqa: RUF012

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="auth.role_permissions",
        back_populates="roles",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="auth.user_roles",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role {self.name}>"
