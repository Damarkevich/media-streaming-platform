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
    echo=settings.sql_echo,
    future=True,
    connect_args={
        "server_settings": {"search_path": f"{settings.postgres_db_schema},public"}
    },
)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped asynchronous SQLAlchemy session."""
    async with async_session() as session:
        yield session


async def check_postgres() -> bool:
    """Check the connection to PostgreSQL by executing a simple query."""
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return False
