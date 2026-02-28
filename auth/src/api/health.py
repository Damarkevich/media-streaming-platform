from fastapi import APIRouter

from src.db.postgres import check_postgres
from src.db.redis import check_redis

router = APIRouter(redirect_slashes=False)


@router.get("/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    """Health check endpoint to verify the status of Redis and PostgreSQL services."""
    redis_ok = await check_redis()
    postgres_ok = await check_postgres()

    status = "healthy" if redis_ok and postgres_ok else "unhealthy"

    return {
        "status": status,
        "services": {
            "redis": "up" if redis_ok else "down",
            "postgres": "up" if postgres_ok else "down",
        },
    }
