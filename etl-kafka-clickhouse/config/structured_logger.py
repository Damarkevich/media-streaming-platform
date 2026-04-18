"""Structured JSON logging formatter for batch ETL processes."""

import contextvars
import json
import logging
from typing import Any
from uuid import uuid4

# Context variable for batch_id (used in batch ETL processes instead of request_id)
batch_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "batch_id", default=None
)


class BatchJsonFormatter(logging.Formatter):
    """JSON formatter for batch processes that includes batch_id if available."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with batch_id for batch ETL processes.

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

        # Inject batch_id from context if available (for batch processes)
        batch_id = batch_id_context.get()
        if batch_id:
            log_dict["batch_id"] = batch_id

        # Add exception info if present
        if record.exc_info:
            log_dict["exception"] = self.formatException(record.exc_info)

        # Add module and function info
        log_dict["module"] = record.module
        log_dict["function"] = record.funcName

        return json.dumps(log_dict, default=str)


def set_batch_id(batch_id: str | None = None) -> str:
    """Set or generate batch_id in context for batch tracking.

    Args:
        batch_id: Optional batch ID. If not provided, generates a new UUID.

    Returns:
        The batch_id that was set in context.
    """
    if batch_id is None:
        batch_id = f"batch-{uuid4()}"
    batch_id_context.set(batch_id)
    return batch_id
