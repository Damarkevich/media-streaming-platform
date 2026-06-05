from fastapi import APIRouter

from src.db.postgres import check_postgres

router = APIRouter(redirect_slashes=False)


@router.get("/health")
async def health_check() -> dict[str, str | dict[str, str]]:
    postgres_ok = await check_postgres()
    return {
        "status": "healthy" if postgres_ok else "unhealthy",
        "services": {
            "postgres": "up" if postgres_ok else "down",
        },
    }
