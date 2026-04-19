from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from src.api import health
from src.api.v1 import bookmarks, ratings, reviews
from src.core.authorization import require_ugc_access
from src.core.config import settings
from src.core.token_models import TokenPayload
from src.db import mongo
from src.db.mongo import ensure_indexes


TEST_DATABASE_NAME = f"{settings.mongodb_database}_test"


@pytest.fixture(scope="session")
def user_token_payload() -> TokenPayload:
    now = int(time.time())
    return TokenPayload(
        sub=uuid4(),
        jti=uuid4(),
        iat=now,
        exp=now + 3600,
        nbf=now,
        type="access",
        roles=[settings.subscriber_role_name],
    )


@pytest_asyncio.fixture
async def mongo_client() -> AsyncGenerator[AsyncMongoClient, None]:
    client = AsyncMongoClient(settings.mongodb_uri)
    try:
        await client.admin.command("ping")
    except Exception as exc:
        pytest.fail(f"MongoDB is unavailable for tests: {exc}")

    mongo.client = client
    original_database_name = settings.mongodb_database
    settings.mongodb_database = TEST_DATABASE_NAME
    await ensure_indexes()

    yield client

    await client.drop_database(TEST_DATABASE_NAME)
    settings.mongodb_database = original_database_name
    await client.close()
    mongo.client = None


@pytest_asyncio.fixture(autouse=True)
async def clean_test_db(mongo_client: AsyncMongoClient) -> AsyncGenerator[None, None]:
    db = mongo_client[TEST_DATABASE_NAME]
    await db.bookmarks.delete_many({})
    await db.reviews.delete_many({})
    await db.ratings.delete_many({})
    yield
    await db.bookmarks.delete_many({})
    await db.reviews.delete_many({})
    await db.ratings.delete_many({})


@pytest.fixture
def test_db(mongo_client: AsyncMongoClient) -> AsyncDatabase:
    return mongo_client[TEST_DATABASE_NAME]


@pytest_asyncio.fixture
async def async_client(
    mongo_client: AsyncMongoClient,
    user_token_payload: TokenPayload,
) -> AsyncGenerator[AsyncClient, None]:
    async def fake_require_ugc_access() -> TokenPayload:
        return user_token_payload

    test_app = FastAPI()
    test_app.include_router(health.router, prefix="/api", tags=["health"])
    test_app.include_router(bookmarks.router, prefix="/api/v1", tags=["bookmarks"])
    test_app.include_router(ratings.router, prefix="/api/v1", tags=["ratings"])
    test_app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])

    test_app.dependency_overrides[require_ugc_access] = fake_require_ugc_access

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
