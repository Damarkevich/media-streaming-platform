"""Django logging utilities for structured JSON logging with request_id."""

import json
import logging
from typing import Any

from config.middleware import get_request_id


class RequestIDJsonFormatter(logging.Formatter):
    """JSON formatter that injects request_id from context into log records."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with request_id.

        Args:
            record: The log record to format.

        Returns:
            JSON string containing the formatted log record.
        """
        log_dict: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inject request_id from context if available
        request_id = get_request_id()
        if request_id:
            log_dict["request_id"] = request_id

        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)

        # Add module and function info
        log_dict["module"] = record.module
        log_dict["function"] = record.funcName

        return json.dumps(log_dict, default=str)
