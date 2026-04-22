from elasticsearch import AsyncElasticsearch

es: AsyncElasticsearch | None = None


async def get_elastic() -> AsyncElasticsearch:
    if es is None:
        msg = "Elasticsearch client is not initialized"
        raise RuntimeError(msg)
    return es


async def check_es() -> bool:
    """
    Check Elasticsearch connectivity.

    Performs a ping operation to verify that the Elasticsearch client can
    successfully connect to the Elasticsearch cluster.

    Returns:
        bool: True if the connection to Elasticsearch is successful and the
            cluster responds to ping, False if any exception occurs during
            the connection attempt or ping operation.

    Raises:
        Does not raise exceptions; all exceptions are caught and result in
        a False return value.
    """
    try:
        client = await get_elastic()
        result = await client.ping()
    except Exception:
        return False
    else:
        return result is True
