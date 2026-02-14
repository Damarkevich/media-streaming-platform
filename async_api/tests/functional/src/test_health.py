from typing import Any, Callable

import pytest

HEALTH_ENDPOINT = "/api/health"


@pytest.mark.asyncio
async def test_health_check(
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test health endpoint returns expected structure and service statuses."""
    response = await make_get_request(HEALTH_ENDPOINT, {})

    assert response["status"] == 200

    body = response["body"]
    assert "status" in body
    assert "services" in body

    assert body["status"] in {"healthy", "unhealthy"}
    assert "redis" in body["services"]
    assert "elasticsearch" in body["services"]
    assert body["services"]["redis"] in {"up", "down"}
    assert body["services"]["elasticsearch"] in {"up", "down"}
