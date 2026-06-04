from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from src.db.postgres import async_session, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    async with async_session() as session:
        await session.execute(text("SELECT 1"))

    yield

    await engine.dispose()
