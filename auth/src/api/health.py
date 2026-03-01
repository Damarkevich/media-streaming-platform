import logging

from fastapi import APIRouter

from src.db.postgres import check_postgres
from src.db.redis import check_redis

router = APIRouter(redirect_slashes=False)
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    """Health check endpoint to verify the status of Redis and PostgreSQL services."""
    try:
        redis_ok = await check_redis()
    except Exception:
        logger.exception("Redis health check failed with exception")
        redis_ok = False

    try:
        postgres_ok = await check_postgres()
    except Exception:
        logger.exception("PostgreSQL health check failed with exception")
        postgres_ok = False

    status = "healthy" if redis_ok and postgres_ok else "unhealthy"

    return {
        "status": status,
        "services": {
            "redis": "up" if redis_ok else "down",
            "postgres": "up" if postgres_ok else "down",
        },
    }
