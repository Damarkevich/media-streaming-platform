from fastapi import APIRouter

from src.db.elastic import check_es
from src.db.redis import check_redis

router = APIRouter(redirect_slashes=False)


@router.get("/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    """Health check endpoint to verify the status of Redis and Elasticsearch services."""
    redis_ok = await check_redis()
    es_ok = await check_es()

    status = "healthy" if redis_ok and es_ok else "unhealthy"

    return {
        "status": status,
        "services": {
            "redis": "up" if redis_ok else "down",
            "elasticsearch": "up" if es_ok else "down",
        },
    }
