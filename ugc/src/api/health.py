from fastapi import APIRouter, Response, status

from src.db.mongo import check_mongo
from src.db.redis import check_redis

router = APIRouter(redirect_slashes=False)


@router.get("/health")
async def health_check(response: Response) -> dict:
    """Health check endpoint."""
    mongo_ok = await check_mongo()
    redis_ok = await check_redis()

    if not (mongo_ok and redis_ok):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    health_status = "healthy" if mongo_ok and redis_ok else "unhealthy"
    return {
        "status": health_status,
        "services": {
            "mongodb": "up" if mongo_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
    }
