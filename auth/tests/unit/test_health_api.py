import pytest

from src.api.health import health_check


@pytest.mark.asyncio
async def test_health_check_returns_healthy_when_all_services_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _redis_ok() -> bool:
        return True

    async def _postgres_ok() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis", _redis_ok)
    monkeypatch.setattr("src.api.health.check_postgres", _postgres_ok)

    result = await health_check()

    assert result == {
        "status": "healthy",
        "services": {"redis": "up", "postgres": "up"},
    }


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_when_any_service_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _redis_down() -> bool:
        return False

    async def _postgres_ok() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis", _redis_down)
    monkeypatch.setattr("src.api.health.check_postgres", _postgres_ok)

    result = await health_check()

    assert result == {
        "status": "unhealthy",
        "services": {"redis": "down", "postgres": "up"},
    }


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_when_postgres_check_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _redis_ok() -> bool:
        return True

    async def _postgres_error() -> bool:
        raise RuntimeError("db unreachable")

    monkeypatch.setattr("src.api.health.check_redis", _redis_ok)
    monkeypatch.setattr("src.api.health.check_postgres", _postgres_error)

    result = await health_check()

    assert result == {
        "status": "unhealthy",
        "services": {"redis": "up", "postgres": "down"},
    }


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_when_redis_check_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _redis_error() -> bool:
        raise RuntimeError("redis unreachable")

    async def _postgres_ok() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_redis", _redis_error)
    monkeypatch.setattr("src.api.health.check_postgres", _postgres_ok)

    result = await health_check()

    assert result == {
        "status": "unhealthy",
        "services": {"redis": "down", "postgres": "up"},
    }
