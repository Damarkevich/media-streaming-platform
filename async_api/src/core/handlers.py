"""Application-level exception handlers for FastAPI."""

from fastapi import Request
from fastapi.responses import ORJSONResponse

from src.services.exceptions import ServiceUnavailableError


async def service_unavailable_exception_handler(
    request: Request,  # noqa: ARG001
    exc: ServiceUnavailableError,  # noqa: ARG001
) -> ORJSONResponse:
    """Convert service availability errors into unified JSON responses.

    Args:
        request: Current HTTP request.
        exc: Domain exception describing temporary service unavailability.

    Returns:
        ORJSONResponse: HTTP 503 response with a stable error payload.
    """
    return ORJSONResponse(
        status_code=503,
        content={"detail": "Service temporarily unavailable."},
    )
