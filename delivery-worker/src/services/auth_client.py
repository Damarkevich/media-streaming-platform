import logging

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client  # noqa: PLW0603
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=15.0)
    return _client


async def get_user(user_id: str) -> dict | None:
    """Fetch user data from auth internal endpoint. Returns None on error."""
    url = f"{settings.auth_internal_url}/api/v1/users/internal/{user_id}"
    try:
        resp = await get_http_client().get(
            url, headers={"X-Internal-Key": settings.internal_api_key}
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception("Failed to fetch user %s from auth service", user_id)
        return None
