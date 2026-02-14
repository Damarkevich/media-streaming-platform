from typing import Any, Callable
from uuid import uuid4

import pytest

ES_INDEX = "movies"
FILM_DETAILS_ENDPOINT = "/api/v1/films/{film_id}"


@pytest.mark.asyncio
async def test_film_details(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test retrieving detailed information about a specific film by ID."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a film with full details
    genre_id = str(uuid4())
    actor_id = str(uuid4())
    writer_id = str(uuid4())
    director_id = str(uuid4())

    film_data = film_factory(
        title="Detailed Film",
        description="A comprehensive test film with all details",
        imdb_rating=8.7,
        genres_names=["Action", "Sci-Fi"],
        genres=[{"id": genre_id, "name": "Action"}],
        actors_names=["John Doe"],
        actors=[{"id": actor_id, "full_name": "John Doe"}],
        writers_names=["Jane Smith"],
        writers=[{"id": writer_id, "full_name": "Jane Smith"}],
        directors_names=["Bob Director"],
        directors=[{"id": director_id, "full_name": "Bob Director"}],
    )

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": film_data["id"],
            "_source": film_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # Test successful retrieval
    response = await make_get_request(
        FILM_DETAILS_ENDPOINT.format(film_id=film_data["id"]), {}
    )
    assert response["status"] == 200

    body = response["body"]
    assert body["uuid"] == film_data["id"]
    assert body["title"] == "Detailed Film"
    assert body["description"] == "A comprehensive test film with all details"
    assert body["imdb_rating"] == 8.7

    # Check nested structures
    assert len(body["genre"]) == 1
    assert body["genre"][0]["uuid"] == genre_id
    assert body["genre"][0]["name"] == "Action"

    assert len(body["actors"]) == 1
    assert body["actors"][0]["uuid"] == actor_id
    assert body["actors"][0]["full_name"] == "John Doe"

    assert len(body["writers"]) == 1
    assert body["writers"][0]["uuid"] == writer_id
    assert body["writers"][0]["full_name"] == "Jane Smith"

    assert len(body["directors"]) == 1
    assert body["directors"][0]["uuid"] == director_id
    assert body["directors"][0]["full_name"] == "Bob Director"


@pytest.mark.asyncio
async def test_film_details_not_found(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test retrieving a non-existent film returns 404."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a film that doesn't exist
    non_existent_id = str(uuid4())
    response = await make_get_request(
        FILM_DETAILS_ENDPOINT.format(film_id=non_existent_id), {}
    )

    assert response["status"] == 404
    assert "detail" in response["body"]
    assert response["body"]["detail"] == "film not found"


@pytest.mark.asyncio
async def test_film_details_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test that film details are cached."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create a film
    film_data = film_factory(title="Cached Film Details")

    bulk_query: list[dict[str, Any]] = [
        {
            "_index": ES_INDEX,
            "_id": film_data["id"],
            "_source": film_data,
        }
    ]

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(
        FILM_DETAILS_ENDPOINT.format(film_id=film_data["id"]), {}
    )
    assert response1["status"] == 200
    assert response1["body"]["title"] == "Cached Film Details"
    first_result = response1["body"]

    # Remove the film from Elasticsearch to ensure cache is used
    await es_clear_data(ES_INDEX)

    # Second request - should return cached result
    response2 = await make_get_request(
        FILM_DETAILS_ENDPOINT.format(film_id=film_data["id"]), {}
    )
    assert response2["status"] == 200
    assert response2["body"] == first_result


@pytest.mark.asyncio
async def test_film_details_invalid_uuid(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test that invalid UUID format returns 422 validation error."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Try to get a film with invalid UUID format
    response = await make_get_request(
        FILM_DETAILS_ENDPOINT.format(film_id="not-a-valid-uuid"), {}
    )

    assert response["status"] == 422
    assert "detail" in response["body"]
