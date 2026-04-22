from async_fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.api import health
from src.api.v1 import auth, google_oauth, permissions, roles, users
from src.core.config import settings
from src.core.lifespan import lifespan
from src.core.limiter import limiter
from src.core.middleware import request_id_middleware

app = FastAPI(
    title=settings.service_name,
    description=settings.service_description,
    docs_url="/api/auth/docs",
    openapi_url="/api/auth/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

FastAPIInstrumentor.instrument_app(app)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
app.middleware("http")(request_id_middleware)


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(google_oauth.router, prefix="/api/v1/auth", tags=["google_auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(
    permissions.router, prefix="/api/v1/permissions", tags=["permissions"]
)


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(
    request: Request,  # noqa: ARG001
    exc: AuthJWTException,
) -> ORJSONResponse:
    """Translate AuthJWT exceptions into unified JSON HTTP responses."""
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(RateLimitExceeded)
def rate_limit_exception_handler(
    request: Request,  # noqa: ARG001
    exc: RateLimitExceeded,  # noqa: ARG001
) -> ORJSONResponse:
    """Handle rate limit breaches with a unified JSON HTTP response."""
    return ORJSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )
