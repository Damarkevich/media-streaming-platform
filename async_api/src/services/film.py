from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends

from src.db.elastic import get_elastic
from src.models.film import Film


class FilmService:
    """
    Service class for managing film data retrieval from Elasticsearch.

    Attributes:
        elastic (AsyncElasticsearch): Elasticsearch client for querying film data.

    Methods:
        get_by_id(film_id: str) -> Film | None:
            Retrieve a film document by its ID.

        get_list(page_size: int, page_number: int, sort: str) -> list[Film]:
            Retrieve a paginated list of films with sorting.

        _prepare_es_sort_params(sort: str) -> list[dict[str, str]]:
            Prepare Elasticsearch sort parameters from a sort string.
    """

    def __init__(self, elastic: AsyncElasticsearch):
        self.elastic = elastic

    async def get_by_id(self, film_id: str) -> Film | None:
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
        sort_fields = []
        for field in sort.split(","):
            order = "asc"
            if field.startswith("-"):
                order = "desc"
                field = field[1:]
            sort_fields.append({field: order})
        return sort_fields

    async def get_list(self, page_size: int, page_number: int, sort: str):
        """
        Retrieve a paginated list of films from Elasticsearch.

        This method queries the 'movies' index in Elasticsearch with pagination
        and sorting parameters, then converts the results into Film objects.

        Args:
            page_size (int): The number of films to return per page.
            page_number (int): The zero-indexed page number to retrieve.
            sort (str): Sort parameter string that will be processed by
                _prepare_es_sort_params to generate Elasticsearch sort parameters.

        Returns:
            list[Film]: A list of Film objects created from the Elasticsearch results.
                Returns an empty list if no films are found or if a NotFoundError occurs.

        Raises:
            This method catches NotFoundError internally and returns an empty list,
            so it does not propagate exceptions to the caller.
        """

        sort_params = self._prepare_es_sort_params(sort)
        try:
            doc = await self.elastic.search(
                index="movies",
                from_=page_number * page_size,
                size=page_size,
                sort=sort_params,
            )
        except NotFoundError:
            return []
        films = [Film(**item["_source"]) for item in doc["hits"]["hits"]]
        return films


@lru_cache()  # Cache the FilmService instance to avoid redundant creations
def get_film_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
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
