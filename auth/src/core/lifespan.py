from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from src.core.config import settings
from src.db import postgres, redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage the lifespan of the FastAPI application.
    This async context manager handles the startup and shutdown events for the application.
    On startup, it initializes connections to Redis and PostgreSQL services.
    On shutdown, it ensures that all connections are properly closed.

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control is yielded back to the application during its runtime.

    Note:
        This function uses the global redis.redis and postgres.engine objects to store
        the connection instances, making them accessible throughout the application.
    """
    redis.redis = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True,
    )

    from src.models.entity import User

    _ = User

    await postgres.create_database()

    yield

    if redis.redis:
        await redis.redis.close()
    if postgres.engine:
        await postgres.purge_database()
