import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from src.core.config import settings
from src.core.tracer import configure_tracer, shutdown_tracer
from src.db import mongo, redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    configure_tracer()

    redis.redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True,
    )

    mongo.client = AsyncMongoClient(settings.mongodb_uri)

    await mongo.ensure_indexes()

    try:
        await mongo.client.admin.command("ping")
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", e)
        raise

    yield

    if redis.redis:
        await redis.redis.close()

    if mongo.client:
        await mongo.client.close()

    shutdown_tracer()
