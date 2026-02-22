from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.api.v1 import auth
from src.core.config import settings
from src.core.lifespan import lifespan

app = FastAPI(
    title=settings.project_name,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
