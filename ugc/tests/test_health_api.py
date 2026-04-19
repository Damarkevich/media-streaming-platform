from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.api import health as health_module


@pytest.mark.asyncio
async def test_health_returns_200_when_dependencies_are_up(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mongo_up() -> bool:
        return True

    async def redis_up() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_mongo", mongo_up)
    monkeypatch.setattr(health_module, "check_redis", redis_up)

    response = await async_client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["services"] == {"mongodb": "up", "redis": "up"}


@pytest.mark.asyncio
async def test_health_returns_503_when_any_dependency_is_down(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mongo_down() -> bool:
        return False

    async def redis_up() -> bool:
        return True

    monkeypatch.setattr(health_module, "check_mongo", mongo_down)
    monkeypatch.setattr(health_module, "check_redis", redis_up)

    response = await async_client.get("/api/health")

    assert response.status_code == 503
    assert response.json()["status"] == "unhealthy"
    assert response.json()["services"] == {"mongodb": "down", "redis": "up"}
