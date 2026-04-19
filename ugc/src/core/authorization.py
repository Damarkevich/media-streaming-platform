import http
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException

from src.core.authentication import authentication
from src.core.config import settings
from src.core.token_models import TokenPayload


def has_any_role(token_payload: TokenPayload, allowed_roles: set[str]) -> bool:
    roles = token_payload.roles
    if not isinstance(roles, list):
        return False
    return any(role in allowed_roles for role in roles)


def require_roles(*roles: str) -> Callable[..., Awaitable[TokenPayload]]:
    """Build dependency that requires the authenticated user to have any role."""
    required_roles = set(roles)

    async def dependency(
        token_payload: Annotated[TokenPayload, Depends(authentication)],
    ) -> TokenPayload:
        if not has_any_role(token_payload, required_roles):
            raise HTTPException(
                status_code=http.HTTPStatus.FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return token_payload

    return dependency


require_ugc_access = require_roles(
    settings.subscriber_role_name,
    settings.admin_role_name,
)
