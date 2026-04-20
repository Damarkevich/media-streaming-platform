import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text

from src.core.config import settings
from src.core.tracer import configure_tracer, shutdown_tracer
from src.db import postgres, redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager.

    Handles startup and shutdown events:
    - Configures tracing
    - Initializes global Redis and PostgreSQL connections
    - Closes all connections on shutdown

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None

    Notes:
        Uses global redis.redis and postgres.engine for connection sharing.
    """
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

    # Initialize the PostgreSQL connection by creating a session
    try:
        async with postgres.async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        raise

    yield

    if redis.redis:
        await redis.redis.close()
    if postgres.engine:
        await postgres.engine.dispose()

    shutdown_tracer()
