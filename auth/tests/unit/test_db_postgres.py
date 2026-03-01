from unittest.mock import AsyncMock

import pytest

from src.db import postgres as postgres_module


class _SessionContextManager:
    """Async context manager stub returning predefined session."""

    def __init__(self, session) -> None:
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _ScalarResult:
    """Result stub exposing scalar() for SELECT checks."""

    def __init__(self, value: int) -> None:
        self._value = value

    def scalar(self) -> int:
        return self._value


@pytest.mark.asyncio
async def test_get_session_yields_factory_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure request-scoped session dependency yields session from factory."""
    session = AsyncMock()

    def _fake_async_session():
        return _SessionContextManager(session)

    monkeypatch.setattr(postgres_module, "async_session", _fake_async_session)

    generator = postgres_module.get_session()
    yielded = await anext(generator)

    assert yielded is session

    with pytest.raises(StopAsyncIteration):
        await anext(generator)


@pytest.mark.asyncio
async def test_check_postgres_returns_true_when_select_one_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure PostgreSQL health check returns True on successful SELECT 1."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult(1))

    def _fake_async_session():
        return _SessionContextManager(session)

    monkeypatch.setattr(postgres_module, "async_session", _fake_async_session)

    result = await postgres_module.check_postgres()

    assert result is True


@pytest.mark.asyncio
async def test_check_postgres_returns_false_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure PostgreSQL health check returns False when query fails."""
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))

    def _fake_async_session():
        return _SessionContextManager(session)

    monkeypatch.setattr(postgres_module, "async_session", _fake_async_session)

    result = await postgres_module.check_postgres()

    assert result is False
