"""HTTP clients for auth internal API and async-api films list."""

import logging

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
    """Paginate auth internal endpoint to collect all user IDs."""
    ids: list[str] = []
    page = 0
    page_size = 500
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
            break
        data = resp.json()
        items: list[dict] = data.get("items", [])
        ids.extend(item["user_id"] for item in items)
        if len(items) < page_size:
            break
        page += 1
    return ids
