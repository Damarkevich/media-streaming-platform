from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from pydantic import UUID4

from src.db.elastic import get_elastic
from src.models.es_models import Film, Genre


class GenreService:
    """
    Service class for managing genre data retrieval from Elasticsearch.

    Attributes:
        elastic (AsyncElasticsearch): Elasticsearch client for querying genre data.

    Methods:
        get_list() -> list[Genre]:
            Retrieve a list of genres.
    """

    index = "genres"

    def __init__(self, elastic: AsyncElasticsearch):
        self.elastic = elastic

    async def get_list(self) -> list[Genre]:
        """
        Retrieve a list of genres from Elasticsearch.

        This method queries the 'movies' index in Elasticsearch,
        then converts the results into Genre objects.

        Returns:
            list[Genre]: A list of Genre objects created from the Elasticsearch results.
                Returns an empty list if no genres are found or if a NotFoundError occurs.

        Raises:
            This method catches NotFoundError internally and returns an empty list,
            so it does not propagate exceptions to the caller.
        """

        try:
            doc = await self.elastic.search(index=self.index)
        except NotFoundError:
            return []
        genres = [Genre(**item["_source"]) for item in doc["hits"]["hits"]]
        return genres

    async def get_by_id(self, genre_id: UUID4) -> Genre | None:
        """
        Retrieve a genre document from Elasticsearch by its ID.

        Args:
            genre_id (UUID4): The unique identifier of the genre to retrieve.

        Returns:
            Genre | None: A Genre object if the document is found, None otherwise.

        Raises:
            This method catches NotFoundError internally and returns None instead of raising.
            Other Elasticsearch exceptions may propagate up.
        """
        try:
            doc = await self.elastic.get(index=self.index, id=str(genre_id))
        except NotFoundError:
            return None
        return Genre(**doc["_source"])


@lru_cache()  # Cache the GenreService instance to avoid redundant creations
def get_genre_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> GenreService:
    """
    Dependency function that creates and returns a GenreService instance.
    This function is used as a FastAPI dependency to inject a GenreService
    with the required Elasticsearch connection.

    Args:
        elastic (AsyncElasticsearch): Async Elasticsearch client for searching genres,
            injected via dependency.

    Returns:
        GenreService: An instance of GenreService configured with the provided
            Elasticsearch client.
    """

    return GenreService(elastic)
