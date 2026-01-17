from typing import Optional

from elasticsearch import AsyncElasticsearch

es: Optional[AsyncElasticsearch] = None


async def get_elastic() -> AsyncElasticsearch:
    if es is None:
        raise RuntimeError("Elasticsearch client is not initialized")
    return es
