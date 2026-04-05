"""HTTP middleware utilities for request preprocessing."""

from fastapi import Request, Response, status
from fastapi.responses import ORJSONResponse
from src.core.config import settings


async def request_id_middleware(request: Request, call_next) -> Response:
    """Validate and propagate request id for every incoming HTTP request.

    In development mode, this middleware is bypassed to simplify testing and debugging.

    Args:
        request: Incoming HTTP request object.
        call_next: Next ASGI/Starlette handler in middleware chain.

    Returns:
        Response: Either a 400 response when request id is missing,
        or downstream response with echoed ``X-Request-Id`` header.
    """
    if settings.development_mode:
        return await call_next(request)

    request_id = request.headers.get("X-Request-Id")
    if not request_id:
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "X-Request-Id is required."},
        )

    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response
