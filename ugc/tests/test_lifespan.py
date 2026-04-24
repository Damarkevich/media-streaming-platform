from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from src.core import lifespan as lifespan_module


class _FakeRedisClient:
    def __init__(self, **kwargs) -> None:
        self.closed = False
        self.ping = AsyncMock(return_value=True)

    async def aclose(self) -> None:
        self.closed = True


class _FakeMongoClient:
    def __init__(self, *args, **kwargs) -> None:
        self.closed = False
        self.admin = MagicMock()
        self.admin.command = AsyncMock(return_value={"ok": 1})

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_lifespan_pings_redis_and_mongo_on_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedisClient()
    fake_mongo = _FakeMongoClient()

    monkeypatch.setattr(lifespan_module, "Redis", lambda **kw: fake_redis)
    monkeypatch.setattr(lifespan_module, "AsyncMongoClient", lambda *a, **kw: fake_mongo)
    monkeypatch.setattr(lifespan_module.mongo, "ensure_indexes", AsyncMock())

    async with lifespan_module.lifespan(FastAPI()):
        fake_redis.ping.assert_awaited_once()
        fake_mongo.admin.command.assert_awaited_once_with("ping")


@pytest.mark.asyncio
async def test_lifespan_raises_when_redis_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedisClient()
    fake_redis.ping = AsyncMock(side_effect=ConnectionError("redis unavailable"))

    monkeypatch.setattr(lifespan_module, "Redis", lambda **kw: fake_redis)

    with pytest.raises(ConnectionError, match="redis unavailable"):
        async with lifespan_module.lifespan(FastAPI()):
            pass  # pragma: no cover


@pytest.mark.asyncio
async def test_lifespan_raises_when_mongo_ping_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedisClient()
    fake_mongo = _FakeMongoClient()
    fake_mongo.admin.command = AsyncMock(side_effect=ConnectionError("mongo unavailable"))

    monkeypatch.setattr(lifespan_module, "Redis", lambda **kw: fake_redis)
    monkeypatch.setattr(lifespan_module, "AsyncMongoClient", lambda *a, **kw: fake_mongo)
    monkeypatch.setattr(lifespan_module.mongo, "ensure_indexes", AsyncMock())

    with pytest.raises(ConnectionError, match="mongo unavailable"):
        async with lifespan_module.lifespan(FastAPI()):
            pass  # pragma: no cover


@pytest.mark.asyncio
async def test_lifespan_closes_redis_and_mongo_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = _FakeRedisClient()
    fake_mongo = _FakeMongoClient()

    monkeypatch.setattr(lifespan_module, "Redis", lambda **kw: fake_redis)
    monkeypatch.setattr(lifespan_module, "AsyncMongoClient", lambda *a, **kw: fake_mongo)
    monkeypatch.setattr(lifespan_module.mongo, "ensure_indexes", AsyncMock())

    async with lifespan_module.lifespan(FastAPI()):
        pass

    assert fake_redis.closed is True
    assert fake_mongo.closed is True
