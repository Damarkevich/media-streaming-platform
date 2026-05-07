"""HTTP clients for auth internal API and async-api films list."""

import logging
from collections.abc import AsyncIterator

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client  # noqa: PLW0603
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def get_top_films(n: int) -> list[dict]:
    """Fetch top-N films sorted by imdb_rating descending from async_api."""
    url = f"{settings.async_api_url}/api/v1/films"
    try:
        resp = await _get_client().get(
            url,
            params={"sort": "-imdb_rating", "page_size": n, "page_number": 1},
            headers={"X-Request-Id": "scheduler-weekly-digest"},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        logger.exception("Failed to fetch top films from async_api")
        return []


async def get_all_user_ids() -> list[str]:
    """Paginate auth internal endpoint and collect all user IDs in memory."""
    ids: list[str] = []
    async for user_id in iter_user_ids():
        ids.append(user_id)
    return ids


async def iter_user_ids(page_size: int = 500) -> AsyncIterator[str]:
    """Stream user IDs page-by-page from auth internal endpoint."""
    page = 0
    while True:
        try:
            resp = await _get_client().get(
                f"{settings.auth_internal_url}/api/v1/users/internal",
                params={"page": page, "page_size": page_size},
                headers={"X-Internal-Key": settings.internal_api_key},
            )
            resp.raise_for_status()
        except Exception:
            logger.exception("Failed to fetch users page=%d from auth service", page)
            raise
        data = resp.json()
        items: list[dict] = data.get("items", [])
        for item in items:
            user_id = item.get("user_id")
            if user_id:
                yield user_id
        if len(items) < page_size:
            break
        page += 1
