from src.db.redis import redis


class RedisClient:
    @staticmethod
    async def set(key: str, value: str, expire: int = 3600) -> None:
        await redis.setex(key, expire, value)

    @staticmethod
    async def get(key: str) -> str | None:
        return await redis.get(key)
