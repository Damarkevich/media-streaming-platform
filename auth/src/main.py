from async_fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse

from src.api import health
from src.api.v1 import auth, permissions, roles, users
from src.core.config import settings
from src.core.lifespan import lifespan

app = FastAPI(
    title=settings.project_name,
    description=settings.project_description,
    docs_url="/api/openapi",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(
    permissions.router, prefix="/api/v1/permissions", tags=["permissions"]
)


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(
    request: Request, exc: AuthJWTException
) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
