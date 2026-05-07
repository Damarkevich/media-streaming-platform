import logging

import redis.asyncio as aioredis

from src.core.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

THROTTLE_KEY_PREFIX = "notif:review_liked"


def get_redis() -> aioredis.Redis:
    global _redis  # noqa: PLW0603
    if _redis is None:
        _redis = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    """Close singleton Redis client if it was initialized."""
    global _redis  # noqa: PLW0603
    if _redis is None:
        return

    await _redis.aclose()
    _redis = None


async def is_throttled(review_author_id: str) -> bool:
    """Return True if this author already received a review_liked email today."""
    key = f"{THROTTLE_KEY_PREFIX}:{review_author_id}"
    return bool(await get_redis().exists(key))


async def set_throttle(review_author_id: str) -> None:
    """Set throttle key with TTL so the author won't be emailed again today."""
    key = f"{THROTTLE_KEY_PREFIX}:{review_author_id}"
    await get_redis().set(key, "1", ex=settings.review_liked_throttle_ttl)
