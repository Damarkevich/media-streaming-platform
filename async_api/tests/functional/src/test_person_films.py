from typing import Any, Callable
from uuid import uuid4

import pytest

PERSONS_INDEX = "persons"
MOVIES_INDEX = "movies"
PERSON_FILMS_ENDPOINT = "/api/v1/persons/{person_id}/film"


@pytest.mark.asyncio
async def test_person_films(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test retrieving films for a specific person by ID."""
    await es_clear_data(PERSONS_INDEX)
    await es_clear_data(MOVIES_INDEX)
    await redis_clear_data()

    first_film_id = str(uuid4())
    second_film_id = str(uuid4())

    person_data = person_factory(
        full_name="Person With Films",
        films=[
            {"id": first_film_id, "roles": ["actor"]},
            {"id": second_film_id, "roles": ["writer"]},
        ],
    )

    person_bulk_query: list[dict[str, Any]] = [
        {
            "_index": PERSONS_INDEX,
            "_id": person_data["id"],
            "_source": person_data,
        }
    ]

    movies_data: list[dict[str, Any]] = [
        film_factory(id=first_film_id, title="First Person Film", imdb_rating=8.1),
        film_factory(id=second_film_id, title="Second Person Film", imdb_rating=7.3),
        film_factory(title="Unrelated Film", imdb_rating=9.9),
    ]

    movies_bulk_query: list[dict[str, Any]] = [
        {
            "_index": MOVIES_INDEX,
            "_id": film["id"],
            "_source": film,
        }
        for film in movies_data
    ]

    await es_write_data(PERSONS_INDEX, person_bulk_query)
    await es_write_data(MOVIES_INDEX, movies_bulk_query)

    response = await make_get_request(
        PERSON_FILMS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response["status"] == 200

    body = response["body"]
    assert len(body) == 2

    returned_ids = {item["uuid"] for item in body}
    assert returned_ids == {first_film_id, second_film_id}
    assert all(
        "uuid" in film and "title" in film and "imdb_rating" in film for film in body
    )


@pytest.mark.asyncio
async def test_person_films_not_found(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test retrieving films for a non-existent person returns 404."""
    await es_clear_data(PERSONS_INDEX)
    await es_clear_data(MOVIES_INDEX)
    await redis_clear_data()

    non_existent_id = str(uuid4())
    response = await make_get_request(
        PERSON_FILMS_ENDPOINT.format(person_id=non_existent_id), {}
    )

    assert response["status"] == 404
    assert "detail" in response["body"]
    assert response["body"]["detail"] == "person not found"


@pytest.mark.asyncio
async def test_person_films_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    person_factory: Callable[..., dict[str, Any]],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test that person films response is cached."""
    await es_clear_data(PERSONS_INDEX)
    await es_clear_data(MOVIES_INDEX)
    await redis_clear_data()

    film_id = str(uuid4())
    person_data = person_factory(
        full_name="Cached Person Films",
        films=[{"id": film_id, "roles": ["actor"]}],
    )

    person_bulk_query: list[dict[str, Any]] = [
        {
            "_index": PERSONS_INDEX,
            "_id": person_data["id"],
            "_source": person_data,
        }
    ]

    movie_data = film_factory(id=film_id, title="Cached Film", imdb_rating=8.9)
    movies_bulk_query: list[dict[str, Any]] = [
        {
            "_index": MOVIES_INDEX,
            "_id": movie_data["id"],
            "_source": movie_data,
        }
    ]

    await es_write_data(PERSONS_INDEX, person_bulk_query)
    await es_write_data(MOVIES_INDEX, movies_bulk_query)

    response1 = await make_get_request(
        PERSON_FILMS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response1["status"] == 200
    assert len(response1["body"]) == 1
    assert response1["body"][0]["title"] == "Cached Film"
    first_result = response1["body"]

    await es_clear_data(MOVIES_INDEX)
    await es_clear_data(PERSONS_INDEX)

    response2 = await make_get_request(
        PERSON_FILMS_ENDPOINT.format(person_id=person_data["id"]), {}
    )
    assert response2["status"] == 200
    assert response2["body"] == first_result


@pytest.mark.asyncio
async def test_person_films_invalid_uuid(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
):
    """Test that invalid UUID format returns 422 validation error."""
    await es_clear_data(PERSONS_INDEX)
    await es_clear_data(MOVIES_INDEX)
    await redis_clear_data()

    response = await make_get_request(
        PERSON_FILMS_ENDPOINT.format(person_id="not-a-valid-uuid"), {}
    )

    assert response["status"] == 422
    assert "detail" in response["body"]
