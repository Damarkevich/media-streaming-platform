from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from src.api import health
from src.api.v1 import films, genres, persons
from src.core.config import settings
from src.core.handlers import service_unavailable_exception_handler
from src.core.lifespan import lifespan
from src.core.middleware import request_id_middleware
from src.services.exceptions import ServiceUnavailableError

app = FastAPI(
    title=settings.project_name,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

if not settings.development_mode:
    app.middleware("http")(request_id_middleware)


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(films.router, prefix="/api/v1/films", tags=["films"])
app.include_router(genres.router, prefix="/api/v1/genres", tags=["genres"])
app.include_router(persons.router, prefix="/api/v1/persons", tags=["persons"])


app.exception_handler(ServiceUnavailableError)(
    service_unavailable_exception_handler,
)
