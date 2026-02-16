from typing import Any, Callable
from uuid import uuid4

import pytest

ES_INDEX = "genres"
GENRES_ENDPOINT = "/api/v1/genres"


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {"page_size": 50},
            {"status": 200, "length": 5},
        ),
        (
            {"page_size": 50, "page_number": 1},
            {"status": 200, "length": 0},
        ),
        (
            {"page_size": 50, "page_number": 2},
            {"status": 200, "length": 0},
        ),
        (
            {},
            {"status": 200, "length": 5},
        ),
        (
            {"page_size": 0},
            {"status": 422, "length": 1},
        ),
        (
            {"page_number": -1},
            {"status": 422, "length": 1},
        ),
        (
            {"page_size": 101},
            {"status": 422, "length": 1},
        ),
    ],
)
@pytest.mark.asyncio
async def test_genres(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    genre_factory: Callable[..., dict[str, Any]],
    query_data: dict[str, Any],
    expected_answer: dict[str, Any],
):
    """Test list with pagination and validation."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        genre_factory(
            name="Genre " + str(i),
        )
        for i in range(5)
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    response_dict = await make_get_request(GENRES_ENDPOINT, query_data)

    body = response_dict["body"]
    status = response_dict["status"]

    assert status == expected_answer["status"]
    assert len(body) == expected_answer["length"]
    if status == 200 and len(body) > 0:
        assert all("uuid" in genre and "name" in genre for genre in body)


@pytest.mark.asyncio
async def test_genres_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    genre_factory: Callable[..., dict[str, Any]],
):
    """Test that search results are cached and returned from cache on repeated requests."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        genre_factory(
            name="Cached Genre",
        )
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(GENRES_ENDPOINT, {})
    assert response1["status"] == 200
    assert len(response1["body"]) == 1
    first_result = response1["body"]

    # Remove the movie from Elasticsearch to ensure that cache is used for the second request
    await es_clear_data(ES_INDEX)

    # Second request with same parameters - should return cached result
    response2 = await make_get_request(GENRES_ENDPOINT, {})
    assert response2["status"] == 200
    assert len(response2["body"]) == 1
    assert response2["body"] == first_result


@pytest.mark.asyncio
async def test_genres_empty(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test that empty database returns empty list, not an error."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Request genres from empty database
    response = await make_get_request(GENRES_ENDPOINT, {})

    assert response["status"] == 200
    assert response["body"] == []
