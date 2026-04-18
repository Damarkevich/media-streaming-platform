"""Structured JSON logging with request_id context injection."""

import contextvars
import json
import logging
from typing import Any

# Context variable to store request_id across async boundaries
request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


class RequestIDJsonFormatter(logging.Formatter):
    """JSON formatter that injects request_id from context into log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with request_id."""
        log_dict: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject request_id from context if available
        request_id = request_id_context.get()
        if request_id:
            log_dict["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)

        # Add extra fields if provided
        # Note: LogRecord can have arbitrary attributes set dynamically
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "taskName",
            ):
                log_dict[key] = value

        return json.dumps(log_dict, default=str)


def set_request_id(request_id: str | None) -> None:
    """Set request_id in context for the current async task."""
    request_id_context.set(request_id)
