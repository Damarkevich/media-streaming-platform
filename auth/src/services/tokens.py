from datetime import timedelta
from typing import Annotated
from uuid import UUID

from async_fastapi_jwt_auth import AuthJWT  # type: ignore[import-untyped]
from fastapi import Depends

from src.core.config import settings
from src.core.jwt import auth_dep
from src.services.redis import RedisClient, get_redis_client


class TokenService:
    """Token-related application service."""

    def __init__(self, auth: AuthJWT, redis_client: RedisClient) -> None:
        """Initialize the service.

        Args:
            auth: Injected AuthJWT instance.

        Returns:
            None.
        """
        self.auth = auth
        self.redis_client = redis_client

    async def issue_tokens(
        self, user_id: UUID, roles_names: list[str], fresh: bool = False
    ) -> tuple[str, str]:
        """Issue new tokens for a user.

        This method can be extended to include additional logic, such as
        recording issued tokens in the database or enforcing limits on active
        tokens per user.

        Args:
            user_id: ID of the user for whom to issue tokens.
            roles_names: List of role names associated with the user.
            fresh: Whether the access token should be marked as "fresh".

        Returns:
            A tuple of (access_token, refresh_token).

        Raises:
            Exception: Propagates token generation errors.
        """
        access_token_expires: timedelta = timedelta(
            seconds=settings.access_token_expires
        )
        user_claims: dict[str, list[str]] = {"roles": roles_names}
        access_token = await self.auth.create_access_token(  # pyright: ignore[reportUnknownMemberType]
            subject=str(user_id),
            expires_time=access_token_expires,
            fresh=fresh,
            user_claims=user_claims,
        )
        refresh_token_expires: timedelta = timedelta(
            seconds=settings.refresh_token_expires
        )
        refresh_token = await self.auth.create_refresh_token(  # pyright: ignore[reportUnknownMemberType]
            subject=str(user_id), expires_time=refresh_token_expires
        )
        return access_token, refresh_token

    async def add_token_to_blacklist(self, jti: str, token_type: str) -> None:
        """Blacklist token by JTI in Redis.

        Args:
            jti: Token identifier.
            token_type: JWT type (`access` or `refresh`).

        Returns:
            None.

        Raises:
            Exception: Propagates Redis I/O errors.
        """
        ttl_seconds = (
            settings.access_token_expires
            if token_type == "access"
            else settings.refresh_token_expires
        )

        await self.redis_client.add_token_to_blacklist(
            jti=jti,
            ttl_seconds=ttl_seconds,
            token_type=token_type,
        )


def get_token_service(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    auth: Annotated[AuthJWT, Depends(auth_dep)],
) -> TokenService:
    """FastAPI dependency provider for TokenService.

    Args:
        redis_client: Injected Redis client wrapper.
        auth: Injected AuthJWT instance.

    Returns:
        TokenService instance bound to the current session.
    """
    return TokenService(auth=auth, redis_client=redis_client)
