from redis.asyncio import Redis

redis: Redis | None = None


async def get_redis() -> Redis:
    if redis is None:
        error = RuntimeError("Redis client is not initialized")
        raise error
    return redis


async def check_redis() -> bool:
    try:
        client = await get_redis()
        result = await client.ping()
    except Exception:
        return False
    else:
        return result is True
