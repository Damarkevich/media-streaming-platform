from typing import Any, Callable
from uuid import uuid4

import pytest

ES_INDEX = "genres"
GENRE_DETAILS_ENDPOINT = "/api/v1/genres/{genre_id}"


@pytest.mark.asyncio
async def test_genre_details(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    genre_factory: Callable[..., dict[str, Any]],
):
    """Test retrieving detailed information about a specific genre by ID."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a genre with full details
    genre_data = genre_factory(
        name="Some Genre",
    )

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": genre_data["id"],
            "_source": genre_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # Test successful retrieval
    response = await make_get_request(
        GENRE_DETAILS_ENDPOINT.format(genre_id=genre_data["id"]), {}
    )
    assert response["status"] == 200

    body = response["body"]
    assert body["uuid"] == genre_data["id"]
    assert body["name"] == "Some Genre"


@pytest.mark.asyncio
async def test_genre_details_not_found(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test retrieving a non-existent genre returns 404."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a genre that doesn't exist
    non_existent_id = str(uuid4())
    response = await make_get_request(
        GENRE_DETAILS_ENDPOINT.format(genre_id=non_existent_id), {}
    )

    assert response["status"] == 404
    assert "detail" in response["body"]
    assert response["body"]["detail"] == "genre not found"


@pytest.mark.asyncio
async def test_genre_details_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    genre_factory: Callable[..., dict[str, Any]],
):
    """Test that genre details are cached."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a genre
    genre_data = genre_factory(name="Cached Genre")

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": genre_data["id"],
            "_source": genre_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(
        GENRE_DETAILS_ENDPOINT.format(genre_id=genre_data["id"]), {}
    )
    assert response1["status"] == 200
    assert response1["body"]["name"] == "Cached Genre"
    first_result = response1["body"]

    # Remove the genre from Elasticsearch to ensure cache is used
    await es_clear_data(ES_INDEX)

    # Second request - should return cached result
    response2 = await make_get_request(
        GENRE_DETAILS_ENDPOINT.format(genre_id=genre_data["id"]), {}
    )
    assert response2["status"] == 200
    assert response2["body"] == first_result


@pytest.mark.asyncio
async def test_genre_details_invalid_uuid(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test that invalid UUID format returns 422 validation error."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a genre with invalid UUID format
    response = await make_get_request(
        GENRE_DETAILS_ENDPOINT.format(genre_id="not-a-valid-uuid"), {}
    )

    assert response["status"] == 422
    assert "detail" in response["body"]
