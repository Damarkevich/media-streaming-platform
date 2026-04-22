from fastapi import Depends, FastAPI
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from src.api import health
from src.api.v1 import films, genres, persons
from src.core.authorization import require_content_access
from src.core.config import settings
from src.core.handlers import service_unavailable_exception_handler
from src.core.lifespan import lifespan
from src.core.middleware import request_id_middleware
from src.services.exceptions import ServiceUnavailableError

app = FastAPI(
    title=settings.service_name,
    description=settings.service_description,
    docs_url="/api/content/docs",
    openapi_url="/api/content/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)

if not settings.development_mode:
    app.middleware("http")(request_id_middleware)


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(
    films.router,
    prefix="/api/v1/films",
    tags=["films"],
    dependencies=[Depends(require_content_access)],
)
app.include_router(
    genres.router,
    prefix="/api/v1/genres",
    tags=["genres"],
    dependencies=[Depends(require_content_access)],
)
app.include_router(
    persons.router,
    prefix="/api/v1/persons",
    tags=["persons"],
    dependencies=[Depends(require_content_access)],
)


app.exception_handler(ServiceUnavailableError)(
    service_unavailable_exception_handler,
)
