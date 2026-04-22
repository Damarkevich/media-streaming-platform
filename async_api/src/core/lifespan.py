from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sentry_sdk
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from redis.asyncio import Redis

from src.core.config import settings
from src.core.tracer import configure_tracer, shutdown_tracer
from src.db import elastic, redis


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Manage application startup and shutdown lifecycle.

    Startup actions:
        - Configure OpenTelemetry tracer provider.
        - Initialize Redis and Elasticsearch clients.

    Shutdown actions:
        - Close Redis and Elasticsearch clients.
        - Shutdown tracer provider and flush pending spans.

    Args:
        app: FastAPI application instance.

    Yields:
        None: Control is yielded to the running application.
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
    )

    elastic.es = AsyncElasticsearch(
        hosts=[f"{settings.es_schema}{settings.es_host}:{settings.es_port}"],
        meta_header=False,
    )

    yield

    if redis.redis:
        await redis.redis.close()

    if elastic.es:
        await elastic.es.close()

    shutdown_tracer()
