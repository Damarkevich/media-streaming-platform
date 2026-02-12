import uuid
from typing import Any, AsyncGenerator, Callable

import aiohttp
import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from redis.asyncio import Redis

from tests.functional.settings import test_settings


@pytest_asyncio.fixture
async def es_client() -> AsyncGenerator[AsyncElasticsearch, None]:
    """Create Elasticsearch client."""
    client = AsyncElasticsearch(hosts=test_settings.es_url, verify_certs=False)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Create a new Redis client for each test function."""
    client = Redis(host=test_settings.redis_host, port=test_settings.redis_port)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def aio_client() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Fixture to create an aiohttp client session for making HTTP requests."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest_asyncio.fixture
async def es_write_data(
    es_client: AsyncElasticsearch,
) -> Callable[[list[dict[str, Any]]], Any]:
    """Fixture to write test data to Elasticsearch."""

    async def inner(data: list[dict[str, Any]]):
        await es_client.indices.create(
            index=test_settings.es_index, **test_settings.es_index_mapping
        )

        _, errors = await async_bulk(client=es_client, actions=data)

        await es_client.indices.refresh(index=test_settings.es_index)

        if errors:
            raise Exception("Failed to write data to Elasticsearch")

    return inner


@pytest_asyncio.fixture
async def es_clear_data(es_client: AsyncElasticsearch) -> Callable[[], Any]:
    """Fixture to clear all data from the Elasticsearch."""

    async def inner() -> Any:
        if await es_client.indices.exists(index=test_settings.es_index):
            await es_client.indices.delete(index=test_settings.es_index)

    return inner


@pytest_asyncio.fixture
async def redis_clear_data(redis_client: Redis) -> Callable[[], Any]:
    """Fixture to clear all data from Redis."""

    async def inner() -> None:
        await redis_client.flushdb(asynchronous=True)

    return inner


@pytest_asyncio.fixture
async def make_get_request(aio_client: aiohttp.ClientSession):
    """Fixture to make GET requests to the FastAPI service."""

    async def inner(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = test_settings.service_url + endpoint
        async with aio_client.get(url, params=params) as response:
            body: Any = await response.json()
            return {
                "body": body,
                "status": response.status,
                "headers": response.headers,
            }

    return inner


@pytest.fixture
def film_factory():
    """Factory fixture to create film test data with customizable fields."""

    def _create_film(**kwargs: Any) -> dict[str, Any]:
        default: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "imdb_rating": 8.5,
            "genres_names": ["Action", "Sci-Fi"],
            "title": "Test Film",
            "description": "Test description",
            "directors_names": ["Director"],
            "actors_names": ["Actor"],
            "writers_names": ["Writer"],
            "directors": [{"id": str(uuid.uuid4()), "full_name": "Director"}],
            "actors": [{"id": str(uuid.uuid4()), "full_name": "Actor"}],
            "writers": [{"id": str(uuid.uuid4()), "full_name": "Writer"}],
        }
        return {**default, **kwargs}

    return _create_film
