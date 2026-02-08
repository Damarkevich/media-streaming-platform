import uuid
import pytest
from tests.functional.settings import test_settings


@pytest.mark.parametrize(
    "query_data, expected_answer",
    [
        (
            {"query": "The Star", "page_size": 50},
            {
                "status": 200,
                "length": 50,
            },
        ),
        (
            {"query": "Mashed potato", "page_size": 50},
            {
                "status": 200,
                "length": 0,
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_search(es_write_data, make_get_request, query_data, expected_answer):

    es_data = [
        {
            "id": str(uuid.uuid4()),
            "imdb_rating": 8.5,
            "genres_names": ["Action", "Sci-Fi"],
            "title": "The Star",
            "description": "New World",
            "directors_names": ["Stan"],
            "actors_names": ["Ann", "Bob"],
            "writers_names": ["Ben", "Howard"],
            "directors": [
                {"id": "d1f76c67-c0fe-477e-8766-3ab3ff2574b5", "full_name": "Stan"},
            ],
            "actors": [
                {"id": "ef86b8ff-3c82-4d31-ad8e-72b69f4e3f95", "full_name": "Ann"},
                {"id": "fb111f22-121e-44a7-b78f-b19191810fbf", "full_name": "Bob"},
            ],
            "writers": [
                {"id": "caf76c67-c0fe-477e-8766-3ab3ff2574b5", "full_name": "Ben"},
                {"id": "b45bd7bc-2e16-46d5-b125-983d356768c6", "full_name": "Howard"},
            ],
        }
        for _ in range(60)
    ]

    bulk_query: list[dict] = []
    for row in es_data:
        data = {"_index": test_settings.es_index, "_id": row["id"]}
        data.update({"_source": row})
        bulk_query.append(data)

    await es_write_data(bulk_query)

    response_dict = await make_get_request("/api/v1/films/search", query_data)

    body = response_dict["body"]
    status = response_dict["status"]

    assert status == expected_answer["status"]
    assert len(body) == expected_answer["length"]
