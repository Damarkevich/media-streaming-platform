"""Django middleware for request_id propagation and logging context injection."""

import contextvars
import logging
from typing import Callable

# Context variable to store request_id across async boundaries
request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)

logger = logging.getLogger(__name__)


class RequestIDMiddleware:
    """Middleware to validate and propagate request_id for every HTTP request."""

    def __init__(self, get_response: Callable):
        """Initialize middleware with Django's get_response callable.

        Args:
            get_response: The next middleware or view callable in the Django stack.
        """
        self.get_response = get_response

    def __call__(self, request):
        """Process request and inject request_id into response headers.

        Args:
            request: Django HTTP request.

        Returns:
            Django HTTP response with X-Request-Id header.
        """
        # Try to get request_id from headers (preferring nginx-provided value)
        request_id = request.META.get("HTTP_X_REQUEST_ID")

        if not request_id:
            # Log warning but don't fail in development mode
            logger.warning("X-Request-Id header is missing from request")
            return self.get_response(request)

        # Inject request_id into context for logging
        set_request_id(request_id)

        # Store in request object for use in views
        request.request_id = request_id

        response = self.get_response(request)

        # Add request_id to response headers
        response["X-Request-Id"] = request_id

        return response


def set_request_id(request_id: str | None) -> None:
    """Set request_id in context for the current request.

    Args:
        request_id: The request ID to store in context.
    """
    request_id_context.set(request_id)


def get_request_id() -> str | None:
    """Get current request_id from context.

    Returns:
        The request_id if set, None otherwise.
    """
    return request_id_context.get()
