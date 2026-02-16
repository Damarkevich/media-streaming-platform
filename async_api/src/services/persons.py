import logging
from functools import lru_cache
from typing import Any

from elasticsearch import AsyncElasticsearch, ConnectionError, NotFoundError
from fastapi import Depends
from pydantic import UUID4

from src.db.elastic import get_elastic
from src.models.es_models import Person
from src.services.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class PersonService:
    """
    Service class for managing person data retrieval from Elasticsearch.

    Attributes:
        elastic (AsyncElasticsearch): Elasticsearch client for querying person data.

    Methods:
        search(page_size: int, page_number: int, query: str | None = None) -> list[Person]:
            Search for persons based on a query string.

        get_by_id(person_id: str) -> Person | None:
            Retrieve a person document by its ID.

        _prepare_es_query_params(query: str | None = None) -> dict | None:
            Prepare Elasticsearch query parameters for searching persons.
    """

    index = "persons"

    def __init__(self, elastic: AsyncElasticsearch) -> None:
        self.elastic = elastic

    async def search(
        self,
        page_size: int,
        page_number: int,
        query: str | None = None,
    ) -> list[Person]:
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
            logger.error(f"Elasticsearch connection error: {e}")
            raise ServiceUnavailableError("Elasticsearch service is unavailable")

        return [Person(**item["_source"]) for item in doc["hits"]["hits"]]

    async def get_by_id(self, person_id: UUID4) -> Person | None:
        """
        Retrieve a person document from Elasticsearch by its ID.

        Args:
            person_id (UUID4): The unique identifier of the person to retrieve.

        Returns:
            Person | None: A Person object if the document is found, None otherwise.

        Raises:
            This method catches NotFoundError internally and returns None instead of raising.
            Other Elasticsearch exceptions may propagate up.
        """
        try:
            doc = await self.elastic.get(index=self.index, id=str(person_id))
        except NotFoundError:
            return None
        except ConnectionError as e:
            logger.error(f"Elasticsearch connection error: {e}")
            raise ServiceUnavailableError("Elasticsearch service is unavailable")

        return Person(**doc["_source"])

    def _prepare_es_query_params(
        self, query: str | None = None
    ) -> dict[str, Any] | None:
        """
        Prepare Elasticsearch query parameters for searching persons.

        Args:
            query (str | None): The search query string. If None, no text search is applied.

        Returns:
            dict | None: A dictionary representing the Elasticsearch query for searching persons,
                          or None if no search filtering is applied.
        """
        if not query:
            return None

        return {
            "bool": {
                "must": {
                    "match": {
                        "full_name": {
                            "query": query,
                            "fuzziness": "AUTO",
                        }
                    }
                }
            }
        }


@lru_cache()  # Cache the PersonService instance to avoid redundant creations
def get_person_service(
    elastic: AsyncElasticsearch = Depends(get_elastic),
) -> PersonService:
    """
    Dependency function that creates and returns a PersonService instance.
    This function is used as a FastAPI dependency to inject a PersonService
    with the required Elasticsearch connection.
    """

    return PersonService(elastic)
