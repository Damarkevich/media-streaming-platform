from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from scr.db.elastic import get_elastic
from scr.db.redis import get_redis
from scr.models.film import Film

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 minutes


class FilmService:
    """
    Service class for managing film data retrieval from cache and Elasticsearch.

    This service implements a caching strategy where films are first looked up in Redis cache,
    and if not found, retrieved from Elasticsearch and then cached for future requests.

    Attributes:
        redis (Redis): Redis client instance for caching operations.
        elastic (AsyncElasticsearch): Elasticsearch client for querying film data.

    Methods:
        get_by_id(film_id: str) -> Film | None:
            Retrieves a film by its ID, first checking cache then Elasticsearch.

        _get_film_from_elastic(film_id: str) -> Film | None:
            Private method to fetch film data from Elasticsearch index.

        _film_from_cache(film_id: str) -> Film | None:
            Private method to retrieve cached film data from Redis.

        _put_film_to_cache(film: Film):
            Private method to store film data in Redis cache with expiration.
    """

    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Film | None:
        """
        Retrieve a film by its unique identifier.

        This method attempts to fetch a film from the cache first. If the film is not
        found in the cache, it queries Elasticsearch. When retrieved from Elasticsearch,
        the film is stored in the cache for subsequent requests.

        Args:
            film_id (str): The unique identifier of the film to retrieve.

        Returns:
            Film | None: The Film object if found, None otherwise.

        Raises:
            None

        Example:
            >>> film = await film_service.get_by_id("123e4567-e89b-12d3-a456-426614174000")
            >>> if film:
            ...     print(f"Found film: {film.title}")
        """
        film = await self._film_from_cache(film_id)
        if not film:
            print("Film not found in cache, querying Elasticsearch...")
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)
        else:
            print("Film found in cache.")
        return film

    async def _get_film_from_elastic(self, film_id: str) -> Film | None:
        """
        Retrieve a film document from Elasticsearch by its ID.

        Args:
            film_id (str): The unique identifier of the film to retrieve.

        Returns:
            Film | None: A Film object if the document is found, None otherwise.

        Raises:
            This method catches NotFoundError internally and returns None instead of raising.
            Other Elasticsearch exceptions may propagate up.
        """
        try:
            doc = await self.elastic.get(index="movies", id=film_id)
        except NotFoundError:
            return None
        return Film(**doc["_source"])

    async def _film_from_cache(self, film_id: str) -> Film | None:
        """
        Retrieve a film from the Redis cache by its ID.

        This method attempts to fetch a film's data from the Redis cache using the provided
        film ID as the key. If the data exists, it deserializes the JSON string into a Film
        model instance.

        Args:
            film_id (str): The unique identifier of the film to retrieve from cache.

        Returns:
            Film | None: A Film model instance if the film data exists in cache,
                         None if the film is not found in cache.

        Raises:
            ValidationError: If the cached data cannot be properly deserialized into a Film model.
        """
        data = await self.redis.get(film_id)
        if not data:
            return None

        film = Film.model_validate_json(data)
        return film

    async def _put_film_to_cache(self, film: Film) -> None:
        """
        Cache a film object in Redis.

        Args:
            film (Film): The film object to be cached. Must have an 'id' attribute
                         and support model_dump_json() serialization.

        Returns:
            None

        Note:
            The film is stored in Redis with its ID as the key and the JSON-serialized
            film data as the value. The cache entry will expire after FILM_CACHE_EXPIRE_IN_SECONDS.
        """
        await self.redis.set(
            film.id, film.model_dump_json(), FILM_CACHE_EXPIRE_IN_SECONDS
        )


@lru_cache()  # Cache the FilmService instance to avoid redundant creations
def get_film_service(
    redis: Redis = Depends(get_redis),
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    """
    Dependency function that creates and returns a FilmService instance.

    This function is used as a FastAPI dependency to inject a FilmService
    with the required Redis and Elasticsearch connections.

    Args:
        redis (Redis): Redis client instance for caching, injected via dependency.
        elastic (AsyncElasticsearch): Async Elasticsearch client for searching films,
            injected via dependency.

    Returns:
        FilmService: An instance of FilmService configured with the provided
            Redis and Elasticsearch clients.

    Example:
        @app.get("/films/{film_id}")
        async def get_film(
            film_id: str,
            film_service: FilmService = Depends(get_film_service)
        ):
            return await film_service.get_by_id(film_id)
    """

    return FilmService(redis, elastic)
