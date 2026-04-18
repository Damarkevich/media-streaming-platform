import logging

from config.settings import settings
from config.structured_logger import BatchJsonFormatter


def configure_logging() -> None:
    """Configure logging with JSON formatter for batch ETL process."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    json_formatter = BatchJsonFormatter()
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)
