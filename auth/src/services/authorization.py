import logging
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from async_fastapi_jwt_auth import AuthJWT
from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.jwt import auth_dep
from src.db.postgres import get_session
from src.models.role import Permission, PermissionName, RolePermission, UserRole
from src.services.redis import RedisClient, get_redis_client

logger = logging.getLogger(__name__)


class AuthorizationService:
    """Authorization-related application service.

    Provides a reusable API for checking user permissions based on current
    role-to-permission and user-to-role assignments.
    """

    def __init__(self, db: AsyncSession, redis_client: RedisClient):
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.
            redis_client: Injected Redis client wrapper.
        """
        self.db = db
        self.redis_client = redis_client

    async def _get_cached_permissions(
        self,
        user_id: UUID,
    ) -> set[PermissionName] | None:
        permission_values = await self.redis_client.get_cached_user_permissions(user_id)
        if permission_values is None:
            return None
        return {PermissionName(str(value)) for value in permission_values}

    async def _set_cached_permissions(
        self,
        user_id: UUID,
        permissions: set[PermissionName],
    ) -> None:
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

    async def has_permission(self, user_id: UUID, permission: PermissionName) -> bool:
        """Check whether a user has a specific permission.

        Args:
            user_id: The UUID of the user.
            permission: The permission to check.

        Returns:
            True if the user has the permission, otherwise False.
        """
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions


def get_authorization_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
) -> AuthorizationService:
    """FastAPI dependency provider for AuthorizationService.

    Args:
        db: Injected request-scoped async session.
        redis_client: Injected Redis client wrapper.

    Returns:
        AuthorizationService instance bound to the current session.
    """
    return AuthorizationService(db=db, redis_client=redis_client)


async def invalidate_user_permissions_cache(
    redis_client: RedisClient,
    user_id: UUID,
) -> None:
    """Invalidate cached effective permissions for a user.

    Args:
        user_id: The UUID of the user whose permission cache should be invalidated.
    """
    try:
        await redis_client.invalidate_user_permissions_cache(user_id)
    except Exception:
        logger.warning(
            f"Failed to invalidate permission cache for user_id={user_id}",
            exc_info=True,
        )


def require_permission(permission: PermissionName):
    """Build a FastAPI dependency that enforces a specific permission.

    Args:
        permission: Permission required for endpoint access.

    Returns:
        Dependency callable that raises HTTP 403 when permission is missing.
    """

    async def dependency(
        auth: Annotated[AuthJWT, Depends(auth_dep)],
        authorization_service: Annotated[
            AuthorizationService, Depends(get_authorization_service)
        ],
    ) -> None:
        await auth.jwt_required()

        user_id = UUID(str(await auth.get_jwt_subject()))
        if not await authorization_service.has_permission(user_id, permission):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Permission '{permission.value}' is required",
            )

    return dependency
