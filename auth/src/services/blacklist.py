import logging

from sqlalchemy import select

from src.db.postgres import async_session
from src.db.redis import get_redis
from src.models.token import BlacklistedToken

logger = logging.getLogger(__name__)
ACCESS_BLACKLIST_KEY_PREFIX = "blacklist:access:"


class HybridBlacklistChecker:
    """Checks token revocation across Redis (access) and Postgres (refresh)."""

    async def is_token_revoked(self, token_type: str, jti: str) -> bool:
        if token_type == "access":
            return await self._is_access_token_blacklisted(jti)

        if token_type == "refresh":
            return await self._is_refresh_token_blacklisted(jti)

        return False

    async def _is_access_token_blacklisted(self, jti: str) -> bool:
        try:
            redis = await get_redis()
            is_blacklisted = await redis.get(f"{ACCESS_BLACKLIST_KEY_PREFIX}{jti}")
            return is_blacklisted is not None
        except Exception:
            logger.exception("Access-token blacklist check failed")
            return True

    async def _is_refresh_token_blacklisted(self, jti: str) -> bool:
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(BlacklistedToken).where(BlacklistedToken.jti == jti)
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            logger.exception("Refresh-token blacklist check failed")
            return True


blacklist_checker = HybridBlacklistChecker()


def get_blacklist_checker() -> HybridBlacklistChecker:
    return blacklist_checker
