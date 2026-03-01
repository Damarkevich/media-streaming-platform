from unittest.mock import AsyncMock

import pytest

from src.db import redis as redis_module


@pytest.mark.asyncio
async def test_get_redis_raises_when_not_initialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure get_redis fails fast when global client is not initialized."""
    monkeypatch.setattr(redis_module, "redis", None)

    with pytest.raises(RuntimeError, match="not initialized"):
        await redis_module.get_redis()


@pytest.mark.asyncio
async def test_get_redis_returns_initialized_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure get_redis returns the initialized global Redis client."""
    client = AsyncMock()
    monkeypatch.setattr(redis_module, "redis", client)

    result = await redis_module.get_redis()

    assert result is client


@pytest.mark.asyncio
async def test_check_redis_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure Redis health check returns True when ping succeeds."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)

    async def _fake_get_redis():
        return client

    monkeypatch.setattr(redis_module, "get_redis", _fake_get_redis)

    result = await redis_module.check_redis()

    assert result is True


@pytest.mark.asyncio
async def test_check_redis_returns_false_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure Redis health check returns False when any error occurs."""

    async def _fake_get_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(redis_module, "get_redis", _fake_get_redis)

    result = await redis_module.check_redis()

    assert result is False
