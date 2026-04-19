from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from pymongo.asynchronous.database import AsyncDatabase


@pytest.mark.asyncio
async def test_movie_rating_lifecycle_and_stats(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    set_like = await async_client.put(
        f"/api/v1/movies/{movie_id}/rating",
        json={"value": 10},
    )
    my_rating = await async_client.get(f"/api/v1/movies/{movie_id}/rating/my")
    stats = await async_client.get(f"/api/v1/movies/{movie_id}/rating")

    assert set_like.status_code == 200
    assert my_rating.status_code == 200
    assert stats.status_code == 200
    assert my_rating.json()["value"] == 10
    assert stats.json()["rating_count"] == 1
    assert stats.json()["rating_avg"] == 10

    set_dislike = await async_client.put(
        f"/api/v1/movies/{movie_id}/rating",
        json={"value": 0},
    )
    updated_stats = await async_client.get(f"/api/v1/movies/{movie_id}/rating")

    assert set_dislike.status_code == 200
    assert updated_stats.status_code == 200
    assert updated_stats.json()["rating_count"] == 1
    assert updated_stats.json()["rating_avg"] == 0

    removed = await async_client.delete(f"/api/v1/movies/{movie_id}/rating")
    missing = await async_client.get(f"/api/v1/movies/{movie_id}/rating/my")

    assert removed.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Rating not found."


@pytest.mark.asyncio
async def test_review_rating_requires_existing_review(
    async_client: AsyncClient,
    test_db: AsyncDatabase,
) -> None:
    missing_review_id = uuid4()

    set_resp = await async_client.put(
        f"/api/v1/reviews/{missing_review_id}/rating",
        json={"value": 10},
    )
    get_resp = await async_client.get(f"/api/v1/reviews/{missing_review_id}/rating/my")
    del_resp = await async_client.delete(f"/api/v1/reviews/{missing_review_id}/rating")

    assert set_resp.status_code == 404
    assert get_resp.status_code == 404
    assert del_resp.status_code == 404
    assert set_resp.json()["detail"] == "Review not found."
    assert await test_db.ratings.count_documents({}) == 0


@pytest.mark.asyncio
async def test_review_rating_lifecycle(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    review = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "review for rating"},
    )
    review_id = review.json()["id"]

    set_like = await async_client.put(
        f"/api/v1/reviews/{review_id}/rating",
        json={"value": 10},
    )
    get_like = await async_client.get(f"/api/v1/reviews/{review_id}/rating/my")

    assert set_like.status_code == 200
    assert get_like.status_code == 200
    assert get_like.json()["value"] == 10

    set_dislike = await async_client.put(
        f"/api/v1/reviews/{review_id}/rating",
        json={"value": 0},
    )
    get_dislike = await async_client.get(f"/api/v1/reviews/{review_id}/rating/my")

    assert set_dislike.status_code == 200
    assert get_dislike.status_code == 200
    assert get_dislike.json()["value"] == 0

    removed = await async_client.delete(f"/api/v1/reviews/{review_id}/rating")
    missing = await async_client.get(f"/api/v1/reviews/{review_id}/rating/my")

    assert removed.status_code == 204
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Rating not found."
