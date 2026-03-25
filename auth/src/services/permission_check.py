import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.permissions import PermissionName
from src.db.postgres import get_session
from src.models.role import Permission, RolePermission, UserRole
from src.models.user import User
from src.services.redis import RedisClient, get_redis_client

logger = logging.getLogger(__name__)


class PermissionCheckService:
    """Permission-check application service.

    Provides a reusable API for checking user permissions based on current
    role-to-permission and user-to-role assignments.
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

    async def _get_cached_permissions(
        self,
        user_id: UUID,
    ) -> set[PermissionName] | None:
        """Read cached effective permissions for a user.

        Args:
            user_id: User identifier.

        Returns:
            Set of permissions, or None when cache entry is absent.

        Raises:
            Exception: Propagates Redis/cache decode failures to caller.
        """
        permission_values = await self.redis_client.get_cached_user_permissions(user_id)
        if permission_values is None:
            return None
        return {PermissionName(str(value)) for value in permission_values}

    async def _set_cached_permissions(
        self,
        user_id: UUID,
        permissions: set[PermissionName],
    ) -> None:
        """Store effective permissions for a user in cache.

        Args:
            user_id: User identifier.
            permissions: Effective permission set to cache.

        Returns:
            None.

        Raises:
            Exception: Propagates Redis write failures to caller.
        """
        await self.redis_client.set_cached_user_permissions(
            user_id=user_id,
            permissions={permission.value for permission in permissions},
            ttl_seconds=settings.permissions_cache_ttl,
        )

    async def get_user_permissions(self, user_id: UUID) -> set[PermissionName]:
        """Get all effective permissions of a user.

        Args:
            user_id: The UUID of the user.

        Returns:
            A set of effective permissions assigned through user roles.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        try:
            cached_permissions = await self._get_cached_permissions(user_id)
            if cached_permissions is not None:
                return cached_permissions
        except Exception:
            logger.warning(
                f"Failed to read permission cache for user_id={user_id}",
                exc_info=True,
            )

        stmt = (
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        result = await self.db.execute(stmt)
        permissions = {PermissionName(str(value)) for value in result.scalars().all()}

        try:
            await self._set_cached_permissions(user_id, permissions)
        except Exception:
            logger.warning(
                f"Failed to write permission cache for user_id={user_id}",
                exc_info=True,
            )

        return permissions

    async def _is_superuser(self, user_id: UUID) -> bool:
        """Check whether user has superuser flag enabled.

        Args:
            user_id: User identifier.

        Returns:
            True when user has `is_superuser=True`.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        stmt = select(User.is_superuser).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is True

    async def has_permission(self, user_id: UUID, permission: PermissionName) -> bool:
        """Check whether a user has a specific permission.

        Args:
            user_id: The UUID of the user.
            permission: The permission to check.

        Returns:
            True if the user has the permission, otherwise False.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        if await self._is_superuser(user_id):
            return True

        permissions = await self.get_user_permissions(user_id)
        return permission in permissions


def get_permission_check_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
) -> PermissionCheckService:
    """FastAPI dependency provider for PermissionCheckService.

    Args:
        db: Injected request-scoped async session.
        redis_client: Injected Redis client wrapper.

    Returns:
        PermissionCheckService instance bound to the current session.
    """
    return PermissionCheckService(db=db, redis_client=redis_client)


async def invalidate_user_permissions_cache(
    redis_client: RedisClient,
    user_id: UUID,
) -> None:
    """Invalidate cached effective permissions for a user.

    Args:
        redis_client: Redis wrapper used for cache invalidation.
        user_id: The UUID of the user whose permission cache should be invalidated.

    Returns:
        None.
    """
    try:
        await redis_client.invalidate_user_permissions_cache(user_id)
    except Exception:
        logger.warning(
            f"Failed to invalidate permission cache for user_id={user_id}",
            exc_info=True,
        )
