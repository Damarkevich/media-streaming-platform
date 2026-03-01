from datetime import timedelta
from typing import Annotated

from async_fastapi_jwt_auth import AuthJWT
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.jwt import auth_dep
from src.db.postgres import get_session
from src.db.redis import get_redis
from src.models.token import BlacklistedToken


class TokenService:
    """Token-related application service."""

    def __init__(self, db: AsyncSession, auth: AuthJWT, redis: Redis):
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.
            auth: Injected AuthJWT instance.
        """
        self.db = db
        self.auth = auth
        self.redis = redis

    async def issue_tokens(self, user_id: str, fresh: bool = False) -> tuple[str, str]:
        """Issue new tokens for a user.

        This method can be extended to include additional logic, such as
        recording issued tokens in the database or enforcing limits on active
        tokens per user.

        Args:
            user_id: ID of the user for whom to issue tokens.
            fresh: Whether the access token should be marked as "fresh".

        Returns:
            A tuple of (access_token, refresh_token).
        """
        access_token_expires = timedelta(seconds=settings.access_token_expires)
        access_token = await self.auth.create_access_token(
            subject=user_id, expires_time=access_token_expires, fresh=fresh
        )
        refresh_token_expires = timedelta(seconds=settings.refresh_token_expires)
        refresh_token = await self.auth.create_refresh_token(
            subject=user_id, expires_time=refresh_token_expires
        )
        return access_token, refresh_token

    async def add_access_to_blacklist(self, jti: str):
        await self.redis.setex(
            name=f"blacklist:access:{jti}",
            time=settings.access_token_expires,
            value="true",
        )

    async def add_refresh_to_blacklist(self, jti: str):
        stmt = (
            insert(BlacklistedToken)
            .values(jti=jti)
            .on_conflict_do_nothing(index_elements=[BlacklistedToken.jti])
        )
        await self.db.execute(stmt)
        await self.db.commit()


def get_token_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    redis: Annotated[Redis, Depends(get_redis)],
    auth: Annotated[AuthJWT, Depends(auth_dep)],
) -> TokenService:
    """FastAPI dependency provider for TokenService.

    Args:
        db: Injected request-scoped async session.
        redis: Injected Redis client instance.
        auth: Injected AuthJWT instance.

    Returns:
        TokenService instance bound to the current session.
    """
    return TokenService(db=db, redis=redis, auth=auth)
