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
    """Fetch user data from auth internal endpoint.

    Returns None only for 404 (user not found).
    Raises on transport/HTTP errors so callers can apply retries.
    """
    url = f"{settings.auth_internal_url}/api/v1/users/internal/{user_id}"
    try:
        resp = await get_http_client().get(
            url, headers={"X-Internal-Key": settings.internal_api_key}
        )
    except httpx.HTTPError:
        logger.exception("Failed to fetch user %s from auth service", user_id)
        raise

    if resp.status_code == 404:
        return None

    try:
        resp.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Auth service returned error for user %s", user_id)
        raise

    return resp.json()
