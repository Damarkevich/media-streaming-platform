import uuid
from typing import Annotated

from async_fastapi_jwt_auth import AuthJWT
from fastapi import Depends, HTTPException, status

from src.core.config import settings


@AuthJWT.load_config
def _get_authjwt_config():  # type: ignore[misc]
    return settings


async def require_admin(authorize: Annotated[AuthJWT, Depends()]) -> None:
    """Dependency: validates JWT and asserts caller has the 'admin' role."""
    await authorize.jwt_required()
    raw_jwt = await authorize.get_raw_jwt()
    roles: list[str] = raw_jwt.get("roles", []) if raw_jwt else []
    if "admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


async def get_current_user_id(authorize: Annotated[AuthJWT, Depends()]) -> uuid.UUID:
    """Dependency: returns the authenticated user's UUID from JWT subject."""
    await authorize.jwt_required()
    subject = await authorize.get_jwt_subject()
    return uuid.UUID(str(subject))
