import time
import uuid
from typing import Any, AsyncGenerator, Callable

import aiohttp
import pytest
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from jose import jwt
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


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Build Authorization headers with a valid access token for protected endpoints."""
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 3600,
            "nbf": now,
            "type": "access",
            "fresh": True,
            "roles": [test_settings.subscriber_role_name],
        },
        test_settings.authjwt_secret_key,
        algorithm=test_settings.authjwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def request_id_headers() -> dict[str, str]:
    """Build request id header required by the application middleware."""
    return {"X-Request-Id": str(uuid.uuid4())}


@pytest_asyncio.fixture
async def es_write_data(
    es_client: AsyncElasticsearch,
) -> Callable[[str, list[dict[str, Any]]], Any]:
    """Fixture to write test data to Elasticsearch."""

    async def inner(index: str, data: list[dict[str, Any]]):
        if not await es_client.indices.exists(index=index):
            await es_client.indices.create(
                index=index, **test_settings.es_index_mapping(index)
            )

        _, errors = await async_bulk(client=es_client, actions=data)

        await es_client.indices.refresh(index=index)

        if errors:
            raise Exception("Failed to write data to Elasticsearch")

    return inner


@pytest_asyncio.fixture
async def es_clear_data(es_client: AsyncElasticsearch) -> Callable[[str], Any]:
    """Fixture to clear all data from the Elasticsearch."""

    async def inner(index: str) -> Any:
        if await es_client.indices.exists(index=index):
            await es_client.delete_by_query(
                index=index,
                query={"match_all": {}},
                conflicts="proceed",
                refresh=True,
            )
            await es_client.indices.refresh(index=index)

    return inner


@pytest_asyncio.fixture
async def redis_clear_data(redis_client: Redis) -> Callable[[], Any]:
    """Fixture to clear all data from Redis."""

    async def inner() -> None:
        await redis_client.flushdb(asynchronous=True)

    return inner


@pytest_asyncio.fixture
async def make_get_request(
    aio_client: aiohttp.ClientSession,
    auth_headers: dict[str, str],
    request_id_headers: dict[str, str],
):
    """Fixture to make GET requests to the FastAPI service."""

    async def inner(
        endpoint: str,
        params: dict[str, Any] | None = None,
        include_auth: bool = True,
    ) -> dict[str, Any]:
        url = test_settings.service_url + endpoint
        headers = dict(request_id_headers)
        if include_auth and endpoint != "/api/health":
            headers.update(auth_headers)
        async with aio_client.get(url, params=params, headers=headers) as response:
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


@pytest.fixture
def person_factory():
    """Factory fixture to create person test data with customizable fields."""

    def _create_person(**kwargs: Any) -> dict[str, Any]:
        default: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "full_name": "Test Person",
            "films": [{"id": str(uuid.uuid4()), "roles": ["actor"]}],
        }
        return {**default, **kwargs}

    return _create_person


@pytest.fixture
def genre_factory():
    """Factory fixture to create genre test data with customizable fields."""

    def _create_genre(**kwargs: Any) -> dict[str, Any]:
        default: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "name": "Test Genre",
        }
        return {**default, **kwargs}

    return _create_genre
