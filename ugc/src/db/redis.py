from redis.asyncio import Redis

redis: Redis | None = None


async def get_redis() -> Redis:
    if redis is None:
        raise RuntimeError("Redis client is not initialized")
    return redis


async def check_redis() -> bool:
    try:
        client = await get_redis()
        result = await client.ping()
        return result is True
    except Exception:
        return False
