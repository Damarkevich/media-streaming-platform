from typing import Any, Callable

import pytest

ES_INDEX = "persons"
PERSONS_SEARCH_ENDPOINT = "/api/v1/persons/search"


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {"query": "John Doe", "page_size": 50},
            {"status": 200, "length": 50},
        ),
        (
            {"query": "John Doe", "page_size": 50, "page_number": 1},
            {"status": 200, "length": 10},
        ),
        (
            {"query": "John Doe", "page_size": 50, "page_number": 2},
            {"status": 200, "length": 0},
        ),
        (
            {"query": "John Doe", "page_size": 10},
            {"status": 200, "length": 10},
        ),
        (
            {"query": "Nonexistent Person", "page_size": 50},
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
            {"query": "John Doe", "page_size": 0},
            {"status": 422, "length": 1},
        ),
        (
            {"query": "John Doe", "page_number": -1},
            {"status": 422, "length": 1},
        ),
        (
            {"query": "John Doe", "page_size": 101},
            {"status": 422, "length": 1},
        ),
    ],
)
@pytest.mark.asyncio
async def test_persons_search(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
    query_data: dict[str, Any],
    expected_answer: dict[str, Any],
):
    """Test persons search with pagination and validation."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        person_factory(
            full_name="John Doe",
        )
        for _ in range(60)
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    response_dict = await make_get_request(PERSONS_SEARCH_ENDPOINT, query_data)

    body = response_dict["body"]
    status = response_dict["status"]

    assert status == expected_answer["status"]
    assert len(body) == expected_answer["length"]
    if status == 200 and len(body) > 0:
        assert all("uuid" in person and "full_name" in person for person in body)


@pytest.mark.asyncio
async def test_persons_search_by_phrase(
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
):
    """Test search by multi-word phrase in person's full name."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        person_factory(
            full_name="John Smith",
        ),
        person_factory(
            full_name="Jane Smith",
        ),
        person_factory(
            full_name="Bob Johnson",
        ),
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # Search by full name
    response_dict = await make_get_request(
        PERSONS_SEARCH_ENDPOINT, {"query": "John Smith", "page_size": 10}
    )
    assert response_dict["status"] == 200
    assert len(response_dict["body"]) >= 1

    # Check that person with "John Smith" is returned
    person_ids = {p["uuid"] for p in response_dict["body"]}
    assert es_data[0]["id"] in person_ids, (
        "Expected person with 'John Smith' in results"
    )

    # Search by last name
    response_dict = await make_get_request(
        PERSONS_SEARCH_ENDPOINT, {"query": "Smith", "page_size": 10}
    )
    assert response_dict["status"] == 200
    assert len(response_dict["body"]) >= 2

    # Check that both persons with "Smith" are returned
    person_ids = {p["uuid"] for p in response_dict["body"]}
    expected_ids = {es_data[0]["id"], es_data[1]["id"]}
    assert len(person_ids & expected_ids) == 2, (
        "Expected both persons with 'Smith' in results"
    )


@pytest.mark.asyncio
async def test_persons_search_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
):
    """Test that search results are cached and returned from cache on repeated requests."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        person_factory(
            full_name="Cached Person",
        )
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(
        PERSONS_SEARCH_ENDPOINT, {"query": "Cached Person", "page_size": 10}
    )
    assert response1["status"] == 200
    assert len(response1["body"]) == 1
    first_result = response1["body"]

    # Remove the person from Elasticsearch to ensure that cache is used for the second request
    await es_clear_data(ES_INDEX)

    # Second request with same parameters - should return cached result
    response2 = await make_get_request(
        PERSONS_SEARCH_ENDPOINT, {"query": "Cached Person", "page_size": 10}
    )
    assert response2["status"] == 200
    assert len(response2["body"]) == 1
    assert response2["body"] == first_result

    # Different parameters - should not use cache
    response3 = await make_get_request(
        PERSONS_SEARCH_ENDPOINT, {"query": "Cached Person", "page_size": 5}
    )
    assert response3["status"] == 200
    assert len(response3["body"]) == 0
