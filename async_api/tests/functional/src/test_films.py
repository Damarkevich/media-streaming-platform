from typing import Any, Callable
from uuid import uuid4

import pytest

ES_INDEX = "movies"
FILMS_ENDPOINT = "/api/v1/films"


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {"page_size": 50},
            {"status": 200, "length": 50},
        ),
        (
            {"page_size": 50, "page_number": 1},
            {"status": 200, "length": 10},
        ),
        (
            {"page_size": 50, "page_number": 2},
            {"status": 200, "length": 0},
        ),
        (
            {},
            {"status": 200, "length": 10},
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
        (
            {"sort": "title"},
            {"status": 422, "length": 1},
        ),
    ],
)
@pytest.mark.asyncio
async def test_films(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
    query_data: dict[str, Any],
    expected_answer: dict[str, Any],
):
    """Test list with pagination and validation."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        film_factory(
            title="The Star",
        )
        for _ in range(60)
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    response_dict = await make_get_request(FILMS_ENDPOINT, query_data)

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
async def test_films_requires_authorization(
    make_get_request: Callable[[str, dict[str, Any] | None, bool], Any],
):
    """Test films endpoint rejects requests without an access token."""
    response = await make_get_request(FILMS_ENDPOINT, include_auth=False)

    assert response["status"] == 403


@pytest.mark.asyncio
async def test_films_cache(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test that search results are cached and returned from cache on repeated requests."""

    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    es_data: list[dict[str, Any]] = [
        film_factory(
            title="Cached Movie",
        )
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # First request - should hit the database
    response1 = await make_get_request(FILMS_ENDPOINT, {})
    assert response1["status"] == 200
    assert len(response1["body"]) == 1
    first_result = response1["body"]

    # Remove the movie from Elasticsearch to ensure that cache is used for the second request
    await es_clear_data(ES_INDEX)

    # Second request with same parameters - should return cached result
    response2 = await make_get_request(FILMS_ENDPOINT, {})
    assert response2["status"] == 200
    assert len(response2["body"]) == 1
    assert response2["body"] == first_result

    # Different parameters - should not use cache
    response3 = await make_get_request(FILMS_ENDPOINT, {"page_size": 5})
    assert response3["status"] == 200
    assert len(response3["body"]) == 0


@pytest.mark.asyncio
async def test_films_sort_by_rating(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test sorting films by IMDB rating in ascending and descending order."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create films with different ratings
    es_data: list[dict[str, Any]] = [
        film_factory(title="Low Rated Film", imdb_rating=5.0),
        film_factory(title="Medium Rated Film", imdb_rating=7.5),
        film_factory(title="High Rated Film", imdb_rating=9.5),
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # Test descending order (default: -imdb_rating)
    response_desc = await make_get_request(FILMS_ENDPOINT, {"sort": "-imdb_rating"})
    assert response_desc["status"] == 200
    assert len(response_desc["body"]) == 3
    ratings_desc = [film["imdb_rating"] for film in response_desc["body"]]
    assert ratings_desc == [9.5, 7.5, 5.0], (
        "Films should be sorted by rating descending"
    )

    # Test ascending order
    response_asc = await make_get_request(FILMS_ENDPOINT, {"sort": "imdb_rating"})
    assert response_asc["status"] == 200
    assert len(response_asc["body"]) == 3
    ratings_asc = [film["imdb_rating"] for film in response_asc["body"]]
    assert ratings_asc == [5.0, 7.5, 9.5], "Films should be sorted by rating ascending"


@pytest.mark.asyncio
async def test_films_filter_by_genre(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test filtering films by genre ID."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create genre IDs
    action_genre_id = str(uuid4())
    drama_genre_id = str(uuid4())
    comedy_genre_id = str(uuid4())

    # Create films with different genres
    es_data: list[dict[str, Any]] = [
        film_factory(
            title="Action Film 1",
            imdb_rating=8.0,
            genres_names=["Action"],
            genres=[{"id": action_genre_id, "name": "Action"}],
        ),
        film_factory(
            title="Action Film 2",
            imdb_rating=7.5,
            genres_names=["Action"],
            genres=[{"id": action_genre_id, "name": "Action"}],
        ),
        film_factory(
            title="Drama Film",
            imdb_rating=9.0,
            genres_names=["Drama"],
            genres=[{"id": drama_genre_id, "name": "Drama"}],
        ),
        film_factory(
            title="Comedy Film",
            imdb_rating=6.5,
            genres_names=["Comedy"],
            genres=[{"id": comedy_genre_id, "name": "Comedy"}],
        ),
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # Test filtering by Action genre
    response_action = await make_get_request(FILMS_ENDPOINT, {"genre": action_genre_id})
    assert response_action["status"] == 200
    assert len(response_action["body"]) == 2
    titles = [film["title"] for film in response_action["body"]]
    assert all("Action" in title for title in titles), (
        "All films should be Action genre"
    )

    # Test filtering by Drama genre
    response_drama = await make_get_request(FILMS_ENDPOINT, {"genre": drama_genre_id})
    assert response_drama["status"] == 200
    assert len(response_drama["body"]) == 1
    assert response_drama["body"][0]["title"] == "Drama Film"

    # Test filtering by Comedy genre
    response_comedy = await make_get_request(FILMS_ENDPOINT, {"genre": comedy_genre_id})
    assert response_comedy["status"] == 200
    assert len(response_comedy["body"]) == 1
    assert response_comedy["body"][0]["title"] == "Comedy Film"

    # Test with non-existent genre
    non_existent_genre = str(uuid4())
    response_empty = await make_get_request(
        FILMS_ENDPOINT, {"genre": non_existent_genre}
    )
    assert response_empty["status"] == 200
    assert len(response_empty["body"]) == 0


@pytest.mark.asyncio
async def test_films_sort_and_filter_combined(
    es_clear_data: Callable[[str], Any],
    redis_clear_data: Callable[[], Any],
    es_write_data: Callable[[str, list[dict[str, Any]]], Any],
    make_get_request: Callable[[str, dict[str, Any]], Any],
    film_factory: Callable[..., dict[str, Any]],
):
    """Test combining sorting and genre filtering."""
    # Clear existing data to ensure test isolation
    await es_clear_data(ES_INDEX)
    await redis_clear_data()

    # Create genre ID
    action_genre_id = str(uuid4())
    drama_genre_id = str(uuid4())

    # Create films with different genres and ratings
    es_data: list[dict[str, Any]] = [
        film_factory(
            title="Action Film Low",
            imdb_rating=6.0,
            genres_names=["Action"],
            genres=[{"id": action_genre_id, "name": "Action"}],
        ),
        film_factory(
            title="Action Film High",
            imdb_rating=9.0,
            genres_names=["Action"],
            genres=[{"id": action_genre_id, "name": "Action"}],
        ),
        film_factory(
            title="Action Film Medium",
            imdb_rating=7.5,
            genres_names=["Action"],
            genres=[{"id": action_genre_id, "name": "Action"}],
        ),
        film_factory(
            title="Drama Film",
            imdb_rating=10.0,
            genres_names=["Drama"],
            genres=[{"id": drama_genre_id, "name": "Drama"}],
        ),
    ]

    bulk_query: list[dict[str, Any]] = []
    for row in es_data:
        data: dict[str, Any] = {"_index": ES_INDEX, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(ES_INDEX, bulk_query)

    # Test filtering Action genre with descending sort
    response = await make_get_request(
        FILMS_ENDPOINT, {"genre": action_genre_id, "sort": "-imdb_rating"}
    )
    assert response["status"] == 200
    assert len(response["body"]) == 3

    ratings = [film["imdb_rating"] for film in response["body"]]
    titles = [film["title"] for film in response["body"]]

    assert ratings == [9.0, 7.5, 6.0], (
        "Action films should be sorted by rating descending"
    )
    assert all("Action" in title for title in titles), (
        "All films should be Action genre"
    )

    # Test filtering Action genre with ascending sort
    response_asc = await make_get_request(
        FILMS_ENDPOINT, {"genre": action_genre_id, "sort": "imdb_rating"}
    )
    assert response_asc["status"] == 200
    assert len(response_asc["body"]) == 3

    ratings_asc = [film["imdb_rating"] for film in response_asc["body"]]
    assert ratings_asc == [6.0, 7.5, 9.0], (
        "Action films should be sorted by rating ascending"
    )
