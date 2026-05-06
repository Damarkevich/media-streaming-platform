from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from src.db.postgres import check_postgres

router = APIRouter()


@router.get("/health", response_class=ORJSONResponse)
async def health() -> ORJSONResponse:
    db_ok = await check_postgres()
    status = "ok" if db_ok else "degraded"
    return ORJSONResponse({"status": status, "db": db_ok})
