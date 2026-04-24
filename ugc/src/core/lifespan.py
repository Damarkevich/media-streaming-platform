import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from redis.asyncio import Redis

from src.core.config import settings
from src.core.tracer import configure_tracer, shutdown_tracer
from src.db import mongo, redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Manage application startup and shutdown lifecycle."""
    configure_tracer()

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
        )

    redis.redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True,
    )

    try:
        await redis.redis.ping()
    except Exception:
        logger.exception("Failed to connect to Redis")
        raise

    mongo.client = AsyncMongoClient(settings.mongodb_uri)

    await mongo.ensure_indexes()

    try:
        await mongo.client.admin.command("ping")
    except Exception:
        logger.exception("Failed to connect to MongoDB")
        raise

    yield

    if redis.redis:
        await redis.redis.aclose()

    if mongo.client:
        await mongo.client.close()

    shutdown_tracer()
