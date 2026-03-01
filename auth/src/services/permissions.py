import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.models.role import Permission, Role, RolePermission, UserRole
from src.services.permission_check import invalidate_user_permissions_cache
from src.services.redis import RedisClient, get_redis_client

logger = logging.getLogger(__name__)


class RoleNotFoundError(Exception):
    """Raised when the requested role does not exist."""


class PermissionNotFoundError(Exception):
    """Raised when the requested permission does not exist."""


class PermissionService:
    """Permission-related application service.

    This layer encapsulates database operations and translates low-level DB
    exceptions into domain-level errors that API handlers can map to HTTP.
    """

    def __init__(self, db: AsyncSession, redis_client: RedisClient) -> None:
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.
            redis_client: Injected Redis client wrapper.

        Returns:
            None.
        """
        self.db = db
        self.redis_client = redis_client

    async def get_permissions(
        self, page_size: int, page_number: int
    ) -> list[Permission]:
        """Get a paginated list of permissions.

        Args:
            page_size: The number of permissions to return per page.
            page_number: The page number to return (1-based).

        Returns:
            A list of Permission instances for the requested page.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        offset = page_number * page_size
        stmt = (
            select(Permission)
            .offset(offset)
            .limit(page_size)
            .order_by(Permission.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_role_id(self, role_id: UUID) -> list[Permission]:
        """Get a list of permissions assigned to a specific role.

        Args:
            role_id: The UUID of the role.

        Returns:
            A list of Permission instances assigned to the role.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        stmt = (
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
            .order_by(Permission.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """Assign a permission to a role.

        Args:
            role_id: The UUID of the role.
            permission_id: The UUID of the permission.

        Returns:
            None.

        Raises:
            RoleNotFoundError: If role does not exist.
            PermissionNotFoundError: If permission does not exist.
            SQLAlchemyError: If persistence fails.
        """
        if not await self._role_exists(role_id):
            raise RoleNotFoundError("Role not found")
        if not await self._permission_exists(permission_id):
            raise PermissionNotFoundError("Permission not found")

        if await self._role_permission_exists(
            role_id=role_id, permission_id=permission_id
        ):
            return

        role_permission = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(role_permission)
        try:
            await self.db.commit()
            await self._invalidate_role_users_permissions_cache(role_id)
        except IntegrityError:
            await self.db.rollback()
            if await self._role_permission_exists(
                role_id=role_id, permission_id=permission_id
            ):
                return
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        """Remove a permission assignment from a role.

        Args:
            role_id: The UUID of the role.
            permission_id: The UUID of the permission.

        Returns:
            None.

        Raises:
            RoleNotFoundError: If role does not exist.
            PermissionNotFoundError: If permission does not exist.
            SQLAlchemyError: If persistence fails.
        """
        if not await self._role_exists(role_id):
            raise RoleNotFoundError("Role not found")
        if not await self._permission_exists(permission_id):
            raise PermissionNotFoundError("Permission not found")

        stmt = delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        try:
            result = await self.db.execute(stmt)
            if (getattr(result, "rowcount", 0) or 0) == 0:
                return
            await self.db.commit()
            await self._invalidate_role_users_permissions_cache(role_id)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def _role_exists(self, role_id: UUID) -> bool:
        """Return whether role with given ID exists.

        Args:
            role_id: Role identifier.

        Returns:
            True when role exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(Role.id).where(Role.id == role_id))
        return result.scalar_one_or_none() is not None

    async def _permission_exists(self, permission_id: UUID) -> bool:
        """Return whether permission with given ID exists.

        Args:
            permission_id: Permission identifier.

        Returns:
            True when permission exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(
            select(Permission.id).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none() is not None

    async def _role_permission_exists(self, role_id: UUID, permission_id: UUID) -> bool:
        """Return whether role-permission relation already exists.

        Args:
            role_id: Role identifier.
            permission_id: Permission identifier.

        Returns:
            True when relation exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(
            select(RolePermission)
            .where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
            .limit(1)
        )
        return result.scalars().one_or_none() is not None

    async def _invalidate_role_users_permissions_cache(self, role_id: UUID) -> None:
        """Invalidate permission cache for all users assigned to role.

        Args:
            role_id: Role identifier whose related users should be invalidated.

        Returns:
            None.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(
            select(UserRole.user_id).where(UserRole.role_id == role_id)
        )
        user_ids = list(result.scalars().all())
        for user_id in user_ids:
            await invalidate_user_permissions_cache(self.redis_client, user_id)


def get_permission_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
) -> PermissionService:
    """FastAPI dependency provider for PermissionService.

    Args:
        db: Injected request-scoped async session.
        redis_client: Injected Redis client wrapper.

    Returns:
        PermissionService instance bound to the current session.
    """
    return PermissionService(db=db, redis_client=redis_client)
