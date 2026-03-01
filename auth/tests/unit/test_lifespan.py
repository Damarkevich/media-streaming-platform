from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI

from src.core import lifespan as lifespan_module


class _FakeRedisClient:
    """Redis client stub recording close calls."""

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class _FakeEngine:
    """Engine stub recording dispose calls."""

    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


class _SessionContextManager:
    """Async context manager stub returning predefined DB session."""

    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return None


@pytest.mark.asyncio
async def test_lifespan_initializes_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure lifespan opens Redis/DB on startup and closes them on shutdown."""
    fake_session = AsyncMock()
    fake_session.execute = AsyncMock()
    fake_engine = _FakeEngine()

    def _fake_async_session():
        return _SessionContextManager(fake_session)

    monkeypatch.setattr(lifespan_module, "Redis", _FakeRedisClient)
    monkeypatch.setattr(lifespan_module.postgres, "async_session", _fake_async_session)
    monkeypatch.setattr(lifespan_module.postgres, "engine", fake_engine)
    monkeypatch.setattr(lifespan_module.redis, "redis", None)

    async with lifespan_module.lifespan(FastAPI()):
        assert isinstance(lifespan_module.redis.redis, _FakeRedisClient)

    assert lifespan_module.redis.redis is not None
    assert lifespan_module.redis.redis.closed is True
    assert fake_engine.disposed is True
    fake_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_raises_on_postgres_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure lifespan re-raises when startup PostgreSQL check fails."""
    fake_session = AsyncMock()
    fake_session.execute = AsyncMock(side_effect=RuntimeError("db unavailable"))

    def _fake_async_session():
        return _SessionContextManager(fake_session)

    monkeypatch.setattr(lifespan_module, "Redis", _FakeRedisClient)
    monkeypatch.setattr(lifespan_module.postgres, "async_session", _fake_async_session)
    monkeypatch.setattr(lifespan_module.redis, "redis", None)

    with pytest.raises(RuntimeError, match="db unavailable"):
        async with lifespan_module.lifespan(FastAPI()):
            pass
