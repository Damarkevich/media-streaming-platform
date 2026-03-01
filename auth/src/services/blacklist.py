import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import async_session, get_session
from src.models.token import BlacklistedToken
from src.services.redis import RedisClient, create_redis_client, get_redis_client

logger = logging.getLogger(__name__)


class HybridBlacklistChecker:
    """Checks token revocation across Redis (access) and Postgres (refresh)."""

    def __init__(self, redis_client: RedisClient, db: AsyncSession) -> None:
        """Initialize checker dependencies.

        Args:
            redis_client: Redis wrapper for access-token denylist checks.
            db: Async DB session for refresh-token denylist checks.

        Returns:
            None.
        """
        self.redis_client = redis_client
        self.db = db

    async def is_token_revoked(self, token_type: str, jti: str) -> bool:
        """Check whether token is revoked by token type and JTI.

        Args:
            token_type: JWT type (`access` or `refresh`).
            jti: Token identifier.

        Returns:
            True when token is considered revoked.
        """
        if token_type == "access":
            return await self._is_access_token_blacklisted(jti)

        if token_type == "refresh":
            return await self._is_refresh_token_blacklisted(jti)

        return False

    async def _is_access_token_blacklisted(self, jti: str) -> bool:
        """Check access-token revocation in Redis.

        Args:
            jti: Access token identifier.

        Returns:
            True if token is blacklisted or Redis check fails (fail-closed).
        """
        try:
            return await self.redis_client.is_access_token_blacklisted(jti)
        except Exception:
            logger.exception("Access-token blacklist check failed")
            return True

    async def _is_refresh_token_blacklisted(self, jti: str) -> bool:
        """Check refresh-token revocation in PostgreSQL.

        Args:
            jti: Refresh token identifier.

        Returns:
            True if token is blacklisted or DB check fails (fail-closed).
        """
        try:
            result = await self.db.execute(
                select(BlacklistedToken).where(BlacklistedToken.jti == jti)
            )
            return result.scalar_one_or_none() is not None
        except Exception:
            logger.exception("Refresh-token blacklist check failed")
            return True


def get_blacklist_checker(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> HybridBlacklistChecker:
    """Build blacklist checker with request-scoped dependencies.

    Args:
        redis_client: Redis wrapper dependency.
        db: Async DB session dependency.

    Returns:
        Configured `HybridBlacklistChecker` instance.
    """
    return HybridBlacklistChecker(redis_client=redis_client, db=db)


async def check_token_revoked_runtime(token_type: str, jti: str) -> bool:
    """Check token revocation status in runtime JWT callbacks.

    Args:
        token_type: JWT type (`access` or `refresh`).
        jti: Token identifier.

    Returns:
        True if token should be treated as revoked.
    """
    redis_client = await create_redis_client()
    async with async_session() as db:
        checker = HybridBlacklistChecker(redis_client=redis_client, db=db)
        return await checker.is_token_revoked(token_type=token_type, jti=jti)
