import logging

from config.settings import LOG_LEVEL
from config.structured_logger import BatchJsonFormatter


def configure_logging(level: str = LOG_LEVEL) -> None:
    """Configure JSON logging for batch ETL process.

    Args:
        level (str): The logging level to set. Defaults to LOG_LEVEL from settings.

    Call this in the application's entrypoint (e.g. `main.py`) before heavy
    imports if you want to ensure configuration happens before modules create
    their loggers.
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    json_formatter = BatchJsonFormatter()
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)


# Apply a sensible default configuration on import to preserve existing behavior.
configure_logging()
