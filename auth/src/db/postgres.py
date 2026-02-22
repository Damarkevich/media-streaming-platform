import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.core.config import settings

logger = logging.getLogger(__name__)


Base = declarative_base()

dsn = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.sql_host}:{settings.sql_port}/{settings.postgres_db}"
)

engine = create_async_engine(
    dsn,
    echo=True,
    future=True,
    connect_args={
        "server_settings": {"search_path": f"{settings.postgres_db_schema},public"}
    },
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def create_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def purge_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
