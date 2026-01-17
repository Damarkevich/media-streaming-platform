from typing import Optional

from redis.asyncio import Redis

redis: Optional[Redis] = None


async def get_redis() -> Redis:
    if redis is None:
        raise RuntimeError("Redis client is not initialized")
    return redis
