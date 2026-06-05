from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from src.api import health
from src.api.v1 import billing
from src.core.config import settings
from src.core.lifespan import lifespan


def _get_docs_url() -> str | None:
    return "/api/billing/docs" if settings.development_mode else None


def _get_openapi_url() -> str | None:
    return "/api/billing/openapi.json" if settings.development_mode else None


app = FastAPI(
    title=settings.service_name,
    description=settings.service_description,
    docs_url=_get_docs_url(),
    openapi_url=_get_openapi_url(),
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-User-Id", "Stripe-Signature"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["billing"])
