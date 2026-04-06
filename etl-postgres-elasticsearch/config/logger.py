import logging

from config.settings import LOG_FORMAT, LOG_LEVEL


def configure_logging(level: str = LOG_LEVEL, fmt: str = LOG_FORMAT) -> None:
    """C
    onfigure basic logging for the application.

    Args:
        level (str): The logging level to set. Defaults to LOG_LEVEL from settings.
        fmt (str): The logging format to use. Defaults to LOG_FORMAT from settings.

    Call this in the application's entrypoint (e.g. `main.py`) before heavy
    imports if you want to ensure configuration happens before modules create
    their loggers.
    """
    logging.basicConfig(level=level, format=fmt)


# Apply a sensible default configuration on import to preserve existing behavior.
configure_logging()
