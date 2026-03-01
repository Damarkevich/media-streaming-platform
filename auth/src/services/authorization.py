import logging
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from async_fastapi_jwt_auth import AuthJWT
from fastapi import Depends, HTTPException

from src.core.jwt import auth_dep
from src.core.permissions import PermissionName
from src.services.permission_check import (
    PermissionCheckService,
    get_permission_check_service,
)

logger = logging.getLogger(__name__)


async def get_authenticated_user_id(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
) -> UUID:
    """Resolve authenticated user ID from access JWT.

    Args:
        auth: Injected JWT auth dependency.

    Returns:
        UUID of the authenticated user (JWT subject).

    Raises:
        Exception: Propagates JWT validation errors from `jwt_required`.
    """
    await auth.jwt_required()
    return UUID(str(await auth.get_jwt_subject()))


async def get_fresh_authenticated_user_id(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
) -> UUID:
    """Resolve authenticated user ID from fresh access JWT.

    Args:
        auth: Injected JWT auth dependency.

    Returns:
        UUID of the authenticated user (JWT subject).

    Raises:
        Exception: Propagates JWT validation errors from `fresh_jwt_required`.
    """
    await auth.fresh_jwt_required()
    return UUID(str(await auth.get_jwt_subject()))


def require_permission(permission: PermissionName) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency that enforces a specific permission.

    Args:
        permission: Permission required for endpoint access.

    Returns:
        Dependency callable that raises HTTP 403 when permission is missing.
    """

    async def dependency(
        user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
        permission_check_service: Annotated[
            PermissionCheckService, Depends(get_permission_check_service)
        ],
    ) -> None:
        if not await permission_check_service.has_permission(user_id, permission):
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Permission '{permission.value}' is required",
            )

    return dependency
