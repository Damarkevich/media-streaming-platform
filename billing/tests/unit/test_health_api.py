import pytest

from src.api.health import health_check


@pytest.mark.asyncio
async def test_health_check_returns_healthy_when_postgres_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _postgres_ok() -> bool:
        return True

    monkeypatch.setattr("src.api.health.check_postgres", _postgres_ok)

    result = await health_check()

    assert result == {
        "status": "healthy",
        "services": {"postgres": "up"},
    }


@pytest.mark.asyncio
async def test_health_check_returns_unhealthy_when_postgres_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _postgres_down() -> bool:
        return False

    monkeypatch.setattr("src.api.health.check_postgres", _postgres_down)

    result = await health_check()

    assert result == {
        "status": "unhealthy",
        "services": {"postgres": "down"},
    }
