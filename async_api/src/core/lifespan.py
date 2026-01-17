from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from redis.asyncio import Redis

from src.core import config
from src.db import elastic, redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage the lifespan of the FastAPI application.
    This async context manager handles the startup and shutdown events for the application.
    On startup, it initializes connections to Redis and Elasticsearch services.
    On shutdown, it ensures that all connections are properly closed.

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Control is yielded back to the application during its runtime.

    Note:
        This function uses the global redis.redis and elastic.es objects to store
        the connection instances, making them accessible throughout the application.
    """
    redis.redis = Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
    )
    elastic.es = AsyncElasticsearch(
        hosts=[f"{config.ELASTIC_SCHEMA}{config.ELASTIC_HOST}:{config.ELASTIC_PORT}"],
        meta_header=False,
    )

    yield

    if redis.redis:
        await redis.redis.close()
    if elastic.es:
        await elastic.es.close()
