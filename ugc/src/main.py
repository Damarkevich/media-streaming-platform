from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.api import health
from src.api.v1 import bookmarks, ratings, reviews
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.middleware import request_id_middleware


def _get_docs_url() -> str | None:
    return "/api/ugc/docs" if settings.development_mode else None


def _get_openapi_url() -> str | None:
    return "/api/ugc/openapi.json" if settings.development_mode else None


app = FastAPI(
    title=settings.service_name,
    description=settings.service_description,
    docs_url=_get_docs_url(),
    openapi_url=_get_openapi_url(),
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)

app.middleware("http")(request_id_middleware)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(bookmarks.router, prefix="/api/v1", tags=["bookmarks"])
app.include_router(ratings.router, prefix="/api/v1", tags=["ratings"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
