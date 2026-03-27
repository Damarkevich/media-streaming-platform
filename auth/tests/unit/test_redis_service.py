import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.services.redis import RedisClient, create_redis_client, get_redis_client


@pytest.mark.asyncio
async def test_set_get_delete_delegate_to_underlying_client() -> None:
    """Ensure basic set/get/delete operations delegate to raw Redis client."""
    raw_client = AsyncMock()
    raw_client.get = AsyncMock(return_value="value")
    redis_client = RedisClient(raw_client)

    await redis_client.set("key", "value", expire=123)
    value = await redis_client.get("key")
    await redis_client.delete("key")

    raw_client.setex.assert_awaited_once_with("key", 123, "value")
    raw_client.get.assert_awaited_once_with("key")
    raw_client.delete.assert_awaited_once_with("key")
    assert value == "value"


def test_key_builders_produce_expected_prefixes() -> None:
    """Ensure blacklist and permissions cache key builders use expected prefixes."""
    user_id = uuid4()

    access_key = RedisClient.token_blacklist_key("jti-1", token_type="access")
    permissions_key = RedisClient.permissions_cache_key(user_id)

    assert access_key == "blacklist:access:jti-1"
    assert permissions_key == f"auth:user_permissions:{user_id}"


@pytest.mark.asyncio
async def test_get_cached_user_permissions_handles_none_and_bytes() -> None:
    """Ensure cached permissions decode from Redis bytes and handle empty cache."""
    user_id = uuid4()
    raw_client = AsyncMock()
    raw_client.get = AsyncMock(
        side_effect=[None, json.dumps(["roles:read", "roles:update"]).encode()]
    )
    redis_client = RedisClient(raw_client)

    missing = await redis_client.get_cached_user_permissions(user_id)
    populated = await redis_client.get_cached_user_permissions(user_id)

    assert missing is None
    assert populated == {"roles:read", "roles:update"}


@pytest.mark.asyncio
async def test_set_and_invalidate_cached_user_permissions() -> None:
    """Ensure permission cache write serializes values and invalidation deletes key."""
    user_id = uuid4()
    raw_client = AsyncMock()
    redis_client = RedisClient(raw_client)

    await redis_client.set_cached_user_permissions(
        user_id=user_id,
        permissions={"roles:update", "roles:read"},
        ttl_seconds=99,
    )
    await redis_client.invalidate_user_permissions_cache(user_id)

    raw_client.setex.assert_awaited_once_with(
        name=f"auth:user_permissions:{user_id}",
        time=99,
        value='["roles:read", "roles:update"]',
    )
    raw_client.delete.assert_awaited_once_with(f"auth:user_permissions:{user_id}")


@pytest.mark.asyncio
async def test_dependency_providers_return_wrapped_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure dependency providers return RedisClient wrappers."""
    raw_client = AsyncMock()

    from_provider = await get_redis_client(raw_client)

    async def _fake_get_redis():
        return raw_client

    monkeypatch.setattr("src.services.redis.get_redis", _fake_get_redis)
    from_factory = await create_redis_client()

    assert isinstance(from_provider, RedisClient)
    assert from_provider.client is raw_client
    assert isinstance(from_factory, RedisClient)
    assert from_factory.client is raw_client
