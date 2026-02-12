from typing import Any, Callable

import pytest

from tests.functional.settings import test_settings


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {"query": "The Star", "page_size": 50},
            {"status": 200, "length": 50},
        ),
        (
            {"query": "The Star", "page_size": 50, "page_number": 1},
            {"status": 200, "length": 10},
        ),
        (
            {"query": "The Star", "page_size": 50, "page_number": 2},
            {"status": 200, "length": 0},
        ),
        (
            {"query": "The Star", "page_size": 10},
            {"status": 200, "length": 10},
        ),
        (
            {"query": "Mashed potato", "page_size": 50},
            {"status": 200, "length": 0},
        ),
        (
            {},
            {"status": 422, "length": 1},
        ),
        (
            {"query": ""},
            {"status": 422, "length": 1},
        ),
        (
            {"query": "The Star", "page_size": 0},
            {"status": 422, "length": 1},
        ),
        (
            {"query": "The Star", "page_number": -1},
            {"status": 422, "length": 1},
        ),
        (
            {"query": "The Star", "page_size": 101},
            {"status": 422, "length": 1},
        ),
    ],
)
@pytest.mark.asyncio
async def test_search(
    es_clear_data: Callable[[], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
    query_data: dict[str, Any],
    expected_answer: dict[str, Any],
):
    """Test search with pagination and validation."""

    # Clear existing data to ensure test isolation
    await es_clear_data()
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        film_factory(
            title="The Star",
        )
        for _ in range(60)
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": test_settings.es_index, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(bulk_query)

    response_dict = await make_get_request("/api/v1/films/search", query_data)

    body = response_dict["body"]
    status = response_dict["status"]

    assert status == expected_answer["status"]
    assert len(body) == expected_answer["length"]
    if status == 200 and len(body) > 0:
        assert all(
            "uuid" in film and "title" in film and "imdb_rating" in film
            for film in body
        )


@pytest.mark.asyncio
async def test_search_by_phrase(
    es_write_data: Callable[[list[dict[str, Any]]], Any],
    es_clear_data: Callable[[], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test search by multi-word phrase in title and description."""
    # Clear existing data to ensure test isolation
    await es_clear_data()
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        film_factory(
            title="The Star Wars",
            description="Epic space battles",
        ),
        film_factory(
            title="Another Movie",
            description="A story about Star Wars fans",
        ),
        film_factory(
            title="Random Film",
            description="Nothing related",
        ),
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": test_settings.es_index, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(bulk_query)

    # Search by phrase in title
    response_dict = await make_get_request(
        "/api/v1/films/search", {"query": "Star Wars", "page_size": 10}
    )
    assert response_dict["status"] == 200
    assert len(response_dict["body"]) >= 1

    # Check that films with "Star Wars" are returned
    film_ids = {f["uuid"] for f in response_dict["body"]}
    expected_ids = {es_data[0]["id"], es_data[1]["id"]}  # Both have "Star Wars"
    assert len(film_ids & expected_ids) > 0, (
        "Expected films with 'Star Wars' in results"
    )

    # Search by phrase in description
    response_dict = await make_get_request(
        "/api/v1/films/search", {"query": "Star Wars fans", "page_size": 10}
    )
    assert response_dict["status"] == 200
    assert len(response_dict["body"]) >= 1

    # Check that the film with "Star Wars fans" in description is returned
    film_ids = {f["uuid"] for f in response_dict["body"]}
    assert es_data[1]["id"] in film_ids, (
        "Expected film with 'Star Wars fans' in description"
    )


@pytest.mark.asyncio
async def test_search_cache(
    es_clear_data: Callable[[], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test that search results are cached and returned from cache on repeated requests."""

    # Clear existing data to ensure test isolation
    await es_clear_data()
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        film_factory(
            title="Cached Movie",
        )
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": test_settings.es_index, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(
        "/api/v1/films/search", {"query": "Cached Movie", "page_size": 10}
    )
    assert response1["status"] == 200
    assert len(response1["body"]) == 1
    first_result = response1["body"]

    # Remove the movie from Elasticsearch to ensure that cache is used for the second request
    await es_clear_data()

    # Second request with same parameters - should return cached result
    response2 = await make_get_request(
        "/api/v1/films/search", {"query": "Cached Movie", "page_size": 10}
    )
    assert response2["status"] == 200
    assert len(response2["body"]) == 1
    assert response2["body"] == first_result

    # Different parameters - should not use cache
    response3 = await make_get_request(
        "/api/v1/films/search", {"query": "Cached Movie", "page_size": 5}
    )
    assert response3["status"] == 200
    assert len(response3["body"]) == 0
