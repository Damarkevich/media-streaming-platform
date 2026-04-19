from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_bookmark_is_idempotent(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    first = await async_client.put(f"/api/v1/movies/{movie_id}/bookmark")
    second = await async_client.put(f"/api/v1/movies/{movie_id}/bookmark")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["movie_id"] == str(movie_id)
    assert second.json()["movie_id"] == str(movie_id)
    assert first.json()["created_at"] == second.json()["created_at"]


@pytest.mark.asyncio
async def test_list_bookmarks_with_pagination(async_client: AsyncClient) -> None:
    movie_ids = [uuid4() for _ in range(3)]
    for movie_id in movie_ids:
        response = await async_client.put(f"/api/v1/movies/{movie_id}/bookmark")
        assert response.status_code == 200

    page_1 = await async_client.get(
        "/api/v1/bookmarks", params={"page_size": 2, "page_number": 0}
    )
    page_2 = await async_client.get(
        "/api/v1/bookmarks", params={"page_size": 2, "page_number": 1}
    )

    assert page_1.status_code == 200
    assert page_2.status_code == 200
    assert len(page_1.json()) == 2
    assert len(page_2.json()) == 1


@pytest.mark.asyncio
async def test_remove_bookmark_and_404_on_repeat(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    created = await async_client.put(f"/api/v1/movies/{movie_id}/bookmark")
    assert created.status_code == 200

    deleted = await async_client.delete(f"/api/v1/movies/{movie_id}/bookmark")
    deleted_again = await async_client.delete(f"/api/v1/movies/{movie_id}/bookmark")

    assert deleted.status_code == 204
    assert deleted_again.status_code == 404
    assert deleted_again.json()["detail"] == "Bookmark not found."
