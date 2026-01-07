import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from backoff import backoff
from logger import logger

load_dotenv()


ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = os.getenv("ES_PORT", "9200")
ES_SCHEMA_NAME = os.getenv("ES_SCHEMA_NAME", "movies")


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def send_to_elasticsearch(data: list[dict[str, Any]]) -> None:
    """
    Send a batch of records to Elasticsearch using the bulk API.

    This function takes a list of dictionaries representing records and sends them
    to Elasticsearch using the _bulk endpoint. Each record is indexed with its ID.

    Args:
        data (list[dict[str, Any]]): A list of dictionaries where each dictionary
            represents a record to be indexed. Each record must contain an 'id' field.

    Returns:
        None

    Raises:
        The function does not explicitly raise exceptions but logs errors if:
        - The HTTP request fails (non-200 status code)
        - Individual records fail to index (errors in response)
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_SCHEMA_NAME}/_bulk"
    method = "POST"
    headers = {"Content-Type": "application/x-ndjson"}

    bulk_data = ""
    for record in data:
        action = {"index": {"_id": str(record["id"])}}
        bulk_data += f"{json.dumps(action)}\n{json.dumps(record, default=str)}\n"

    response = httpx.request(method, url, headers=headers, content=bulk_data)

    if response.status_code == 200:
        logger.info(f"Successfully sent {len(data)} records to Elasticsearch.")
    else:
        logger.error(
            f"Failed to send data to Elasticsearch. Status code: {response.status_code}, Response: {response.text}"
        )

    if response.json().get("errors"):
        logger.error("Some records failed to index in Elasticsearch.")
