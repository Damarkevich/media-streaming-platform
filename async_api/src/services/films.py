import logging
from functools import lru_cache
from typing import Any

from elasticsearch import AsyncElasticsearch, ConnectionError, NotFoundError
from fastapi import Depends
from pydantic import UUID4

from src.db.elastic import get_elastic
from src.models.es_models import Film
from src.services.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class FilmService:
    """
    Service class for managing film data retrieval from Elasticsearch.

    Attributes:
        elastic (AsyncElasticsearch): Elasticsearch client for querying film data.

    Methods:
        get_list(page_size: int, page_number: int, sort: str) -> list[Film]:
            Retrieve a paginated list of films with sorting.

        search(page_size: int, page_number: int, query: str | None = None) -> list[Film]:
            Search for films based on a query string.

        get_by_id(film_id: str) -> Film | None:
            Retrieve a film document by its ID.

        get_list_by_ids(film_ids: list[UUID4]) -> list[Film]:
            Retrieve a list of film documents by their IDs.

        _prepare_es_sort_params(sort: str) -> list[dict[str, str]]:
            Prepare Elasticsearch sort parameters from a sort string.

        _prepare_es_genre_query_params(genre: UUID4 | None = None) -> dict | None:
            Prepare Elasticsearch query parameters for filtering by genre.

        _prepare_es_query_params(query: str | None = None) -> dict | None:
            Prepare Elasticsearch query parameters for searching films.
    """

    index = "movies"

    def __init__(self, elastic: AsyncElasticsearch) -> None:
        self.elastic = elastic

    async def get_list(
        self,
        page_size: int,
        page_number: int,
        sort: str,
        genre_id: UUID4 | None = None,
    ) -> list[Film]:
        """
        Retrieve a paginated list of films from Elasticsearch.

        This method queries the 'movies' index in Elasticsearch with pagination
        and sorting parameters, then converts the results into Film objects.

        Args:
            page_size (int): The number of films to return per page.
            page_number (int): The zero-indexed page number to retrieve.
            sort (str): Sort parameter string that will be processed by
                _prepare_es_sort_params to generate Elasticsearch sort parameters.
            genre_id (UUID4 | None, optional): Filter films by genre ID. Defaults to None.

        Returns:
            list[Film]: A list of Film objects created from the Elasticsearch results.
                Returns an empty list if no films are found or if a NotFoundError occurs.

        Raises:
            ServiceUnavailableError: If there is a connection error with Elasticsearch.
        """

        sort_params = self._prepare_es_sort_params(sort)
        query_params = self._prepare_es_genre_query_params(genre_id)

        try:
            doc = await self.elastic.search(
                index=self.index,
                from_=page_number * page_size,
                size=page_size,
                sort=sort_params,
                query=query_params,
            )
        except NotFoundError:
            return []
        except ConnectionError as e:
            logger.exception("Elasticsearch connection error")
            msg = "Elasticsearch service is unavailable"
            raise ServiceUnavailableError(msg) from e

        return [Film(**item["_source"]) for item in doc["hits"]["hits"]]

    async def search(
        self,
        page_size: int,
        page_number: int,
        query: str | None = None,
    ) -> list[Film]:
        """
        Search for films in Elasticsearch based on a query string.
        This method queries the 'movies' index in Elasticsearch with pagination
        and search parameters, then converts the results into Film objects.

        Args:
            page_size (int): The number of films to return per page.
            page_number (int): The zero-indexed page number to retrieve.
            query (str | None, optional): The search query string. Defaults to None.

        Returns:
            list[Film]: A list of Film objects created from the Elasticsearch results.
                Returns an empty list if no films are found or if a NotFoundError occurs.

        Raises:
            ServiceUnavailableError: If there is a connection error with Elasticsearch.
        """
        query_params = self._prepare_es_query_params(query)

        try:
            doc = await self.elastic.search(
                index=self.index,
                from_=page_number * page_size,
                size=page_size,
                query=query_params,
            )
        except NotFoundError:
            return []
        except ConnectionError as e:
            logger.exception("Elasticsearch connection error")
            msg = "Elasticsearch service is unavailable"
            raise ServiceUnavailableError(msg) from e

        return [Film(**item["_source"]) for item in doc["hits"]["hits"]]

    async def get_by_id(self, film_id: UUID4) -> Film | None:
        """
        Retrieve a film document from Elasticsearch by its ID.

        Args:
            film_id (UUID4): The unique identifier of the film to retrieve.

        Returns:
            Film | None: A Film object if the document is found, None otherwise.

        Raises:
            ServiceUnavailableError: If there is a connection error with Elasticsearch.
        """
        try:
            doc = await self.elastic.get(index=self.index, id=str(film_id))
        except NotFoundError:
            return None
        except ConnectionError as e:
            logger.exception("Elasticsearch connection error")
            msg = "Elasticsearch service is unavailable"
            raise ServiceUnavailableError(msg) from e

        return Film(**doc["_source"])

    async def get_list_by_ids(self, film_ids: list[UUID4]) -> list[Film]:
        """
        Retrieve a list of film documents from Elasticsearch by their IDs.

        Args:
            film_ids (list[UUID4]): A list of unique identifiers of the films to retrieve.

        Returns:
            list[Film]: A list of Film objects created from the Elasticsearch results.
                Returns an empty list if no films are found or if a NotFoundError occurs.

        Raises:
            ServiceUnavailableError: If there is a connection error with Elasticsearch.
        """
        if not film_ids:
            return []

        try:
            response = await self.elastic.mget(
                index=self.index, ids=[str(film_id) for film_id in film_ids]
            )
        except NotFoundError:
            return []
        except ConnectionError as e:
            logger.exception("Elasticsearch connection error")
            msg = "Elasticsearch service is unavailable"
            raise ServiceUnavailableError(msg) from e

        return [Film(**doc["_source"]) for doc in response["docs"] if doc.get("found")]

    def _prepare_es_sort_params(self, sort: str) -> list[dict[str, str]]:
        """
        Prepare Elasticsearch sort parameters from a comma-separated string.

        Args:
            sort (str): A comma-separated string of field names. Prefix a field with '-'
                        to sort in descending order. Example: "title,-rating,created_at"

        Returns:
            list[dict[str, str]]: A list of dictionaries where each dictionary contains
                                  a field name as key and sort order ('asc' or 'desc') as value.
                                  Example: [{"title": "asc"}, {"rating": "desc"}, {"created_at": "asc"}]

        Example:
            >>> _prepare_es_sort_params("title,-rating")
            [{"title": "asc"}, {"rating": "desc"}]
        """
        sort_fields: list[dict[str, str]] = []
        for field in sort.split(","):
            order = "asc"
            field_name = field
            if field_name.startswith("-"):
                order = "desc"
                field_name = field_name[1:]
            sort_fields.append({field_name: order})
        return sort_fields

    def _prepare_es_genre_query_params(
        self, genre_id: UUID4 | None = None
    ) -> dict[str, Any] | None:
        """
        Prepare Elasticsearch query parameters for filtering by genre.

        Args:
            genre_id (UUID4 | None): The genre ID to filter films by. If None, no filtering is applied.
        Returns:
            dict | None: A dictionary representing the Elasticsearch query for genre filtering,
                          or None if no genre filtering is applied.
        """
        if not genre_id:
            return None

        return {
            "nested": {
                "path": "genres",
                "query": {"term": {"genres.id": str(genre_id)}},
            }
        }

    def _prepare_es_query_params(
        self, query: str | None = None
    ) -> dict[str, Any] | None:
        """
        Prepare Elasticsearch query parameters for searching films.

        Args:
            query (str | None): The search query string. If None, no text search is applied.

        Returns:
            dict | None: A dictionary representing the Elasticsearch query for searching films,
                          or None if no search filtering is applied.
        """
        if not query:
            return None

        return {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",
                            "description",
                        ],
                        "fuzziness": "AUTO",
                    }
                }
            }
        }


@lru_cache  # Cache the FilmService instance to avoid redundant creations
def get_film_service(elastic: AsyncElasticsearch = Depends(get_elastic)) -> FilmService:  # noqa: B008
    """
    Dependency function that creates and returns a FilmService instance.

    This function is used as a FastAPI dependency to inject a FilmService
    with the required Elasticsearch connection.

    Args:
        elastic (AsyncElasticsearch): Async Elasticsearch client for searching films,
            injected via dependency.

    Returns:
        FilmService: An instance of FilmService configured with the provided
            Elasticsearch client.

    Example:
        @app.get("/films/{film_id}")
        async def get_film(
            film_id: str,
            film_service: FilmService = Depends(get_film_service)
        ):
            return await film_service.get_by_id(film_id)
    """

    return FilmService(elastic)
