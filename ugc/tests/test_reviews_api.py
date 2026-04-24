from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from pymongo.asynchronous.database import AsyncDatabase


@pytest.mark.asyncio
async def test_upsert_review_and_get_my_review(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    created = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "initial review"},
    )
    updated = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "updated review"},
    )
    mine = await async_client.get(f"/api/v1/movies/{movie_id}/review/my")

    assert created.status_code == 200
    assert updated.status_code == 200
    assert mine.status_code == 200
    assert created.json()["id"] == updated.json()["id"]
    assert mine.json()["text"] == "updated review"


@pytest.mark.asyncio
async def test_get_review_by_id(async_client: AsyncClient) -> None:
    movie_id = uuid4()

    created = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "review by id"},
    )
    assert created.status_code == 200

    review_id = created.json()["id"]
    fetched = await async_client.get(f"/api/v1/reviews/{review_id}")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == review_id


@pytest.mark.asyncio
async def test_list_reviews_sorted_by_created_at(
    async_client: AsyncClient,
    test_db: AsyncDatabase,
) -> None:
    movie_id = uuid4()

    first = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "api review"},
    )
    assert first.status_code == 200

    older_review_id = str(uuid4())
    await test_db.reviews.insert_one(
        {
            "_id": older_review_id,
            "user_id": str(uuid4()),
            "movie_id": str(movie_id),
            "text": "older review",
            "created_at": datetime(2020, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2020, 1, 1, tzinfo=UTC),
            "rating_count": 0,
            "rating_sum": 0.0,
            "rating_avg": None,
        }
    )

    newest_first = await async_client.get(
        f"/api/v1/movies/{movie_id}/reviews", params={"sort": "-created_at"}
    )
    oldest_first = await async_client.get(
        f"/api/v1/movies/{movie_id}/reviews", params={"sort": "created_at"}
    )

    assert newest_first.status_code == 200
    assert oldest_first.status_code == 200
    assert len(newest_first.json()) == 2
    assert len(oldest_first.json()) == 2
    assert newest_first.json()[0]["id"] != oldest_first.json()[0]["id"]


@pytest.mark.asyncio
async def test_list_reviews_sorted_by_rating_and_paginated(
    async_client: AsyncClient,
    test_db: AsyncDatabase,
) -> None:
    movie_id = uuid4()

    first = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "api review"},
    )
    assert first.status_code == 200
    first_id = first.json()["id"]

    second_id = str(uuid4())
    await test_db.reviews.insert_one(
        {
            "_id": second_id,
            "user_id": str(uuid4()),
            "movie_id": str(movie_id),
            "text": "other user review",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "rating_count": 0,
            "rating_sum": 0.0,
            "rating_avg": None,
        }
    )

    # Rate first review low (0) and second review high (10) via API
    low = await async_client.put(
        f"/api/v1/reviews/{first_id}/rating",
        json={"value": 0},
    )
    assert low.status_code == 200

    high = await async_client.put(
        f"/api/v1/reviews/{second_id}/rating",
        json={"value": 10},
    )
    assert high.status_code == 200

    by_rating = await async_client.get(
        f"/api/v1/movies/{movie_id}/reviews",
        params={"sort": "-rating_avg", "page_size": 1, "page_number": 0},
    )
    by_rating_page_2 = await async_client.get(
        f"/api/v1/movies/{movie_id}/reviews",
        params={"sort": "-rating_avg", "page_size": 1, "page_number": 1},
    )

    assert by_rating.status_code == 200
    assert by_rating_page_2.status_code == 200
    assert len(by_rating.json()) == 1
    assert len(by_rating_page_2.json()) == 1
    assert by_rating.json()[0]["id"] != by_rating_page_2.json()[0]["id"]
    # second review (rating_avg=10) should sort first in descending order
    assert by_rating.json()[0]["id"] == second_id


@pytest.mark.asyncio
async def test_delete_review_cascades_review_ratings(
    async_client: AsyncClient,
    test_db: AsyncDatabase,
) -> None:
    movie_id = uuid4()

    created = await async_client.put(
        f"/api/v1/movies/{movie_id}/review",
        json={"text": "to be deleted"},
    )
    review_id = created.json()["id"]

    rated = await async_client.put(
        f"/api/v1/reviews/{review_id}/rating",
        json={"value": 10},
    )
    assert rated.status_code == 200

    deleted = await async_client.delete(f"/api/v1/movies/{movie_id}/review")
    assert deleted.status_code == 204

    missing_review_rating = await async_client.get(
        f"/api/v1/reviews/{review_id}/rating/my"
    )
    assert missing_review_rating.status_code == 404
    assert missing_review_rating.json()["detail"] == "Review not found."
    assert await test_db.reviews.count_documents({"_id": review_id}) == 0
    assert await test_db.ratings.count_documents({"target_id": review_id}) == 0
