from redis.asyncio import Redis

redis: Redis | None = None


async def get_redis() -> Redis:
    """Return initialized Redis client instance from application state."""
    if redis is None:
        raise RuntimeError("Redis client is not initialized")
    return redis


async def check_redis() -> bool:
    """
    Check if Redis connection is available and responding.

    This function attempts to establish a connection to Redis and verify
    its availability by sending a PING command.

    Returns:
        bool: True if Redis is available and responding to PING command,
              False if connection fails or any exception occurs.

    Raises:
        None: All exceptions are caught and handled internally.
    """

    try:
        client = await get_redis()
        result = await client.ping()  # type: ignore
        return result is True
    except Exception:
        return False
