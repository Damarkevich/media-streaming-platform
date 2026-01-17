import functools
import hashlib
import json
import logging
from typing import Any, Awaitable, Callable, Mapping
from urllib.parse import urlencode

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from src.core.config import settings
from src.db.redis import get_redis

logger = logging.getLogger(__name__)


def normalize_mapping(data: Mapping[str, Any]) -> list[tuple[str, str]]:
    """
    Normalize a mapping into a sorted list of key-value tuples.

    This function converts a dictionary-like mapping into a standardized list of tuples
    suitable for use in cache key generation or URL query parameters. It handles None values,
    scalar values, and collections (lists/tuples) of values.

    Args:
        data (Mapping[str, Any]): A mapping (e.g., dict) containing keys and values.
            Values can be None, scalars, or collections (list/tuple).

    Returns:
        list[tuple[str, str]]: A sorted list of (key, value) tuples where:
            - Keys are sorted alphabetically
            - None values are excluded
            - Collection values are flattened into multiple tuples with the same key
            - Collection values are sorted and converted to strings
            - All values are converted to strings

    Examples:
        >>> normalize_mapping({'b': 2, 'a': 1})
        [('a', '1'), ('b', '2')]

        >>> normalize_mapping({'tags': ['python', 'async'], 'page': 1})
        [('page', '1'), ('tags', 'async'), ('tags', 'python')]

        >>> normalize_mapping({'key': None, 'value': 'test'})
        [('value', 'test')]
    """
    items = []
    for key in sorted(data.keys()):
        value = data[key]
        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            for v in sorted(map(str, value)):
                items.append((key, v))
        else:
            items.append((key, str(value)))
    return items


def canonical_identity(
    method: str,
    path_params: Mapping[str, Any],
    query_params: Mapping[str, Any],
) -> str:
    """
    Generate a canonical identifier string from HTTP request parameters.

    This function creates a URL-encoded string representation of an HTTP request
    by combining the method, path parameters, and query parameters in a normalized
    and deterministic way. This is useful for cache key generation or request
    fingerprinting.

    Args:
        method (str): The HTTP method (e.g., 'GET', 'POST'). Will be converted to uppercase.
        path_params (Mapping[str, Any]): Path parameters from the URL route.
        query_params (Mapping[str, Any]): Query string parameters from the URL.

    Returns:
        str: A URL-encoded string representing the canonical identity of the request,
             with format: "method=METHOD&path:key1=value1&query:key2=value2&..."

    Example:
        >>> canonical_identity('get', {'id': '123'}, {'sort': 'name', 'limit': '10'})
        'method=GET&path:id=123&query:limit=10&query:sort=name'
    """

    parts = [("method", method.upper())]

    parts.extend(("path:" + k, v) for k, v in normalize_mapping(path_params))
    parts.extend(("query:" + k, v) for k, v in normalize_mapping(query_params))

    return urlencode(parts)


def identity_hash(identity: str) -> str:
    """
    Generate a 16-character hash from an identity string.

    Args:
        identity (str): The identity string to be hashed.

    Returns:
        str: A 16-character hexadecimal hash derived from the SHA-256 hash of the input identity.

    Example:
        >>> identity_hash("user123")
        'a665a45920422f9d'
    """
    return hashlib.sha256(identity.encode()).hexdigest()[:16]


def cache() -> Callable[[Callable[..., Awaitable]], Callable[..., Awaitable]]:
    """
    A decorator factory that adds Redis caching to async GET request handlers.

    This decorator caches the results of async functions that handle GET requests,
    using Redis as the cache backend. It automatically extracts the Request object,
    builds a cache key based on the request parameters, and manages cache storage
    and retrieval.

    Returns:
        Callable: A decorator that wraps async functions with caching functionality.

    Cache Behavior:
        - Only GET requests are cached
        - Cache keys are built from function name, method, path params, and query params
        - Cache expiration is controlled by config.CACHE_EXPIRE_IN_SECONDS
        - If Redis is unavailable or operations fail, the function executes normally
        - Results are JSON-serialized before caching

    Example:
        >>> @cache()
        ... async def get_movies(request: Request, page: int = 1):
        ...     return await fetch_movies(page)

    Notes:
        - The decorated function must accept a Request object either as a positional
          or keyword argument
        - Non-GET requests bypass the cache
        - All Redis errors are logged but don't prevent the function from executing
        - Cached data is deserialized from JSON on cache hits
    """

    def decorator(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # 1. Extract Request
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if request is None:
                request = kwargs.get("request")
            if request is None:
                logger.error(
                    "Cache decorator requires 'request' parameter of type Request"
                )
                return await func(*args, **kwargs)
            if request.method != "GET":
                return await func(*args, **kwargs)

            # 2. Build cache key
            identity = canonical_identity(
                method=request.method,
                path_params=request.path_params,
                query_params=request.query_params,
            )
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = f"{func_name}:{identity_hash(identity)}"

            # 3. Get Redis
            redis = None
            try:
                redis = await get_redis()
            except Exception:
                logger.exception(
                    "Failed to get Redis connection; proceeding without cache"
                )
                return await func(*args, **kwargs)

            # 4. Try to get from Redis
            try:
                cached = await redis.get(cache_key)
            except Exception:
                logger.exception(
                    f"Redis cache get failed for key '{cache_key}'; proceeding without cache",
                )
                return await func(*args, **kwargs)

            if cached:
                logger.info(f"Cache hit for key: {cache_key}")
                return json.loads(cached)
            logger.info(f"Cache miss for key: {cache_key}")

            # 5. Execute handler
            result = await func(*args, **kwargs)

            # 6. Store in Redis
            try:
                data = json.dumps(jsonable_encoder(result))
                await redis.set(
                    cache_key,
                    data,
                    ex=settings.cache_expire_in_seconds,
                )
                logger.info(f"Cache set for key: {cache_key}")
            except Exception:
                logger.exception(
                    f"Redis cache set failed for key '{cache_key}'; response not cached",
                )

            return result

        return wrapper

    return decorator
