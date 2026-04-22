import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import httpx
import psycopg
import redis

logger = logging.getLogger(__name__)


def backoff[T](
    start_sleep_time: float = 0.1, factor: int = 2, border_sleep_time: int = 10
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    A decorator that implements an exponential backoff strategy for retrying a function
    upon encountering specific exceptions.

    Args:
        start_sleep_time (float): Initial wait time before the first retry in seconds.
        factor (int): Multiplicative factor for increasing the wait time after each failure.
        border_sleep_time (int): Maximum wait time between retries in seconds.

    Returns:
        Callable: A decorated function with backoff retry logic.
    """

    def func_wrapper(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def inner(*args: Any, **kwargs: Any) -> T:
            n = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except (
                    ConnectionError,
                    TimeoutError,
                    psycopg.OperationalError,
                    psycopg.InterfaceError,
                    httpx.ConnectError,
                    httpx.TimeoutException,
                    httpx.NetworkError,
                    redis.ConnectionError,
                    redis.TimeoutError,
                    redis.BusyLoadingError,
                    redis.RedisError,
                ) as e:
                    sleep_time = min(start_sleep_time * (factor**n), border_sleep_time)
                    logger.warning(
                        f"[backoff] Error: {e}. Retrying in {sleep_time:.2f} seconds..."
                    )
                    time.sleep(sleep_time)
                    n += 1

        return inner

    return func_wrapper
