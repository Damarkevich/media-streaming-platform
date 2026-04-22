"""Flask request_id middleware for event_ingest service."""

from core.structured_logger import set_request_id
from flask import Flask


def init_request_id_middleware(app: Flask) -> None:
    """Register request_id middleware for Flask application.

    Extracts X-Request-Id header from incoming requests and stores in context
    for use in logging.

    Args:
        app: Flask application instance.
    """

    @app.before_request
    def extract_request_id() -> None:
        """Extract request_id from headers before processing request."""
        request_id = get_request_id_from_headers()
        if request_id:
            set_request_id(request_id)

    @app.after_request
    def clear_request_id(response):
        """Clear request_id context after response is sent."""
        set_request_id(None)
        return response


def get_request_id_from_headers() -> str | None:
    """Get request_id from incoming request headers.

    Checks for X-Request-Id header which is passed by nginx.

    Returns:
        Request ID string if present, None otherwise.
    """
    from flask import request  # noqa: PLC0415

    return request.headers.get("X-Request-Id")
