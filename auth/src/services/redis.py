import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from redis.asyncio import Redis

from src.db.redis import get_redis


class RedisClient:
    """Thin async Redis wrapper used by auth services."""

    ACCESS_BLACKLIST_KEY_PREFIX = "blacklist:access:"
    PERMISSIONS_CACHE_KEY_PREFIX = "auth:user_permissions:"

    def __init__(self, client: Redis) -> None:
        """Initialize wrapper with raw async Redis client.

        Args:
            client: Async Redis client instance.

        Returns:
            None.
        """
        self.client = client

    async def set(self, key: str, value: str, expire: int = 3600) -> None:
        """Set key with expiration in seconds.

        Args:
            key: Redis key to write.
            value: Value payload to store.
            expire: TTL in seconds.

        Returns:
            None.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        await self.client.setex(key, expire, value)

    async def get(self, key: str) -> bytes | str | None:
        """Get value by key from Redis.

        Args:
            key: Redis key to fetch.

        Returns:
            Raw value as bytes/str, or None when absent.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        return await self.client.get(key)

    async def delete(self, key: str) -> None:
        """Delete key from Redis.

        Args:
            key: Redis key to delete.

        Returns:
            None.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        await self.client.delete(key)

    @classmethod
    def access_blacklist_key(cls, jti: str) -> str:
        """Build Redis key for access-token blacklist entry.

        Args:
            jti: Access token identifier.

        Returns:
            Redis key for access token denylist entry.
        """
        return f"{cls.ACCESS_BLACKLIST_KEY_PREFIX}{jti}"

    async def add_access_token_to_blacklist(self, jti: str, ttl_seconds: int) -> None:
        """Store access-token JTI in denylist with TTL.

        Args:
            jti: Access token identifier.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            None.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        await self.client.setex(
            name=self.access_blacklist_key(jti),
            time=ttl_seconds,
            value="true",
        )

    async def is_access_token_blacklisted(self, jti: str) -> bool:
        """Return whether access-token JTI exists in denylist.

        Args:
            jti: Access token identifier.

        Returns:
            True when token is blacklisted.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        value = await self.client.get(self.access_blacklist_key(jti))
        return value is not None

    @classmethod
    def permissions_cache_key(cls, user_id: UUID) -> str:
        """Build Redis key for cached user permissions.

        Args:
            user_id: User identifier.

        Returns:
            Redis key for cached permissions entry.
        """
        return f"{cls.PERMISSIONS_CACHE_KEY_PREFIX}{user_id}"

    async def get_cached_user_permissions(self, user_id: UUID) -> set[str] | None:
        """Read cached permission values for user.

        Args:
            user_id: User identifier.

        Returns:
            Permission set, or None when cache entry is absent.

        Raises:
            RedisError: Propagates Redis I/O errors.
            json.JSONDecodeError: If cached JSON payload is malformed.
        """
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
        """Persist user permission cache payload with TTL.

        Args:
            user_id: User identifier.
            permissions: Permission values to cache.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            None.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        payload = json.dumps(sorted(permissions))
        await self.client.setex(
            name=self.permissions_cache_key(user_id),
            time=ttl_seconds,
            value=payload,
        )

    async def invalidate_user_permissions_cache(self, user_id: UUID) -> None:
        """Delete cached permissions for user.

        Args:
            user_id: User identifier.

        Returns:
            None.

        Raises:
            RedisError: Propagates Redis I/O errors.
        """
        await self.client.delete(self.permissions_cache_key(user_id))


async def get_redis_client(
    redis: Annotated[Redis, Depends(get_redis)],
) -> RedisClient:
    """Provide request-scoped Redis service wrapper.

    Args:
        redis: Injected raw Redis client.

    Returns:
        Wrapped Redis client utility.
    """
    return RedisClient(client=redis)


async def create_redis_client() -> RedisClient:
    """Create Redis service wrapper for runtime utility calls.

    Returns:
        Wrapped Redis client utility.

    Raises:
        RedisError: Propagates Redis connection errors.
    """
    redis = await get_redis()
    return RedisClient(client=redis)
