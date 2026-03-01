import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from src.db.redis import get_redis


class RedisClient:
    ACCESS_BLACKLIST_KEY_PREFIX = "blacklist:access:"
    PERMISSIONS_CACHE_KEY_PREFIX = "auth:user_permissions:"

    def __init__(self, client: Redis):
        self.client = client

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        await self.client.setex(key, expire, value)

    async def get(self, key: str) -> bytes | str | None:
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    @classmethod
    def access_blacklist_key(cls, jti: str) -> str:
        return f"{cls.ACCESS_BLACKLIST_KEY_PREFIX}{jti}"

    async def add_access_token_to_blacklist(self, jti: str, ttl_seconds: int) -> None:
        await self.client.setex(
            name=self.access_blacklist_key(jti),
            time=ttl_seconds,
            value="true",
        )

    async def is_access_token_blacklisted(self, jti: str) -> bool:
        value = await self.client.get(self.access_blacklist_key(jti))
        return value is not None

    @classmethod
    def permissions_cache_key(cls, user_id: UUID) -> str:
        return f"{cls.PERMISSIONS_CACHE_KEY_PREFIX}{user_id}"

    async def get_cached_user_permissions(self, user_id: UUID) -> set[str] | None:
        value = await self.client.get(self.permissions_cache_key(user_id))
        if value is None:
            return None

        payload = value.decode() if isinstance(value, bytes) else value
        items = json.loads(payload)
        return {str(item) for item in items}

    async def set_cached_user_permissions(
        self,
        user_id: UUID,
        permissions: set[str],
        ttl_seconds: int,
    ) -> None:
        payload = json.dumps(sorted(permissions))
        await self.client.setex(
            name=self.permissions_cache_key(user_id),
            time=ttl_seconds,
            value=payload,
        )

    async def invalidate_user_permissions_cache(self, user_id: UUID) -> None:
        await self.client.delete(self.permissions_cache_key(user_id))


async def get_redis_client(
    redis: Annotated[Redis, Depends(get_redis)],
) -> RedisClient:
    return RedisClient(client=redis)


async def create_redis_client() -> RedisClient:
    redis = await get_redis()
    return RedisClient(client=redis)
