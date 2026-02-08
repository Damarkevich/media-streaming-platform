import aiohttp
import pytest_asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from tests.functional.settings import test_settings


@pytest_asyncio.fixture
async def es_client():
    """Create a new Elasticsearch client for each test function."""
    client = AsyncElasticsearch(hosts=test_settings.es_url, verify_certs=False)
    yield client
    await client.close()


@pytest_asyncio.fixture
async def es_write_data(es_client):
    """Fixture to write test data to Elasticsearch."""

    async def inner(data: list[dict]):
        if await es_client.indices.exists(index=test_settings.es_index):
            await es_client.indices.delete(index=test_settings.es_index)
        await es_client.indices.create(
            index=test_settings.es_index, **test_settings.es_index_mapping
        )

        _, errors = await async_bulk(client=es_client, actions=data)

        await es_client.indices.refresh(index=test_settings.es_index)

        if errors:
            raise Exception("Ошибка записи данных в Elasticsearch")

    return inner


@pytest_asyncio.fixture
async def aio_client():
    """Fixture to create an aiohttp client session for making HTTP requests."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest_asyncio.fixture
async def make_get_request(aio_client):
    """Fixture to make GET requests to the FastAPI service."""

    async def inner(endpoint: str, params: dict):
        url = test_settings.service_url + endpoint
        async with aio_client.get(url, params=params) as response:
            body = await response.json()
            return {
                "body": body,
                "status": response.status,
                "headers": response.headers,
            }

    return inner
