from typing import Any, Callable
from uuid import uuid4

import pytest

ES_INDEX = "persons"
PERSON_DETAILS_ENDPOINT = "/api/v1/persons/{person_id}"


@pytest.mark.asyncio
async def test_person_details(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
):
    """Test retrieving detailed information about a specific person by ID."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a person with films
    film_id = str(uuid4())
    person_data = person_factory(
        full_name="Detailed Person",
        films=[{"id": film_id, "roles": ["actor", "writer"]}],
    )

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": person_data["id"],
            "_source": person_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # Test successful retrieval
    response = await make_get_request(
        PERSON_DETAILS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response["status"] == 200

    body = response["body"]
    assert body["uuid"] == person_data["id"]
    assert body["full_name"] == "Detailed Person"

    assert len(body["films"]) == 1
    assert body["films"][0]["uuid"] == film_id
    assert body["films"][0]["roles"] == ["actor", "writer"]


@pytest.mark.asyncio
async def test_person_details_not_found(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test retrieving a non-existent person returns 404."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a person that doesn't exist
    non_existent_id = str(uuid4())
    response = await make_get_request(
        PERSON_DETAILS_ENDPOINT.format(person_id=non_existent_id), {}
    )

    assert response["status"] == 404
    assert "detail" in response["body"]
    assert response["body"]["detail"] == "person not found"


@pytest.mark.asyncio
async def test_person_details_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
):
    """Test that person details are cached."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a person
    person_data = person_factory(full_name="Cached Person Details")

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": person_data["id"],
            "_source": person_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(
        PERSON_DETAILS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response1["status"] == 200
    assert response1["body"]["full_name"] == "Cached Person Details"
    first_result = response1["body"]

    # Remove the person from Elasticsearch to ensure cache is used
    await es_clear_data(ES_INDEX)

    # Second request - should return cached result
    response2 = await make_get_request(
        PERSON_DETAILS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response2["status"] == 200
    assert response2["body"] == first_result


@pytest.mark.asyncio
async def test_person_details_invalid_uuid(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test that invalid UUID format returns 422 validation error."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a person with invalid UUID format
    response = await make_get_request(
        PERSON_DETAILS_ENDPOINT.format(person_id="not-a-valid-uuid"), {}
    )

    assert response["status"] == 422
    assert "detail" in response["body"]
