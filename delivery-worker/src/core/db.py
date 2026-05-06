"""SQLAlchemy async engine + session for delivery-worker."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings

dsn = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.sql_host}:{settings.sql_port}/{settings.postgres_db}"
)

engine = create_async_engine(dsn, echo=settings.sql_echo, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
