import json
import logging
from pathlib import Path
from typing import Any

import httpx
from backoff import backoff
from config.etl_mappings import MAPPINGS, Mapping
from config.settings import ES_HOST, ES_PORT

logger = logging.getLogger(__name__)


def get_default_es_index_schema(mapping: Mapping) -> dict[str, Any]:
    """
    Load and return the default Elasticsearch index schema from a JSON file.

    This function reads the Elasticsearch index schema configuration from a predefined
    JSON file and returns it as a dictionary.

    Args:
        mapping (Mapping): The mapping object containing the index file name.

    Returns:
        dict: A dictionary containing the Elasticsearch index schema configuration,
              including mappings, settings, and other index-related properties.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        IOError: If there are issues reading the file.

    Example:
        >>> schema = get_default_es_index_schema()
        >>> print(schema.keys())
        dict_keys(['settings', 'mappings'])
    """
    with Path(mapping.es_index_file).open(encoding="utf-8") as f:
        return json.load(f)


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def remove_es_index(mapping: Mapping) -> None:
    """
    Remove an Elasticsearch index.

    Sends a DELETE request to remove the specified Elasticsearch index. Logs the outcome
    of the operation based on the HTTP response status code.

    Args:
        mapping (Mapping): The mapping object containing the index name to be removed.

    Returns:
        None

    Raises:
        No exceptions are raised explicitly, but HTTP errors are logged.

    Note:
        - If the index is successfully removed (status 200), an info message is logged.
        - If the index does not exist (status 404), an info message is logged.
        - For any other status code, an error message with details is logged.
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{mapping.es_index}"
    method = "DELETE"
    headers = {"Content-Type": "application/json"}

    response = httpx.request(method, url, headers=headers)

    if response.status_code == 200:
        logger.info(f"Elasticsearch index '{mapping.es_index}' removed successfully.")
    elif response.status_code == 404:
        logger.info(f"Elasticsearch index '{mapping.es_index}' does not exist.")
    else:
        logger.error(
            f"Failed to remove Elasticsearch index '{mapping.es_index}'. Status code: {response.status_code}, Response: {response.text}"
        )


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def create_es_index(mapping: Mapping) -> None:
    """
    Create an Elasticsearch index with the default schema.

    This function sends a PUT request to create a new Elasticsearch index using
    the schema retrieved from get_default_es_index_schema(). It handles different
    response scenarios:
    - 200: Index created successfully
    - 400: Index already exists
    - Other: Logs an error with the status code and response text

    Args:
        mapping (Mapping): The mapping object containing the index name and schema file.

    Raises:
        httpx.RequestError: If the HTTP request fails due to network or connection issues.

    Returns:
        None
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{mapping.es_index}"
    method = "PUT"
    headers = {"Content-Type": "application/json"}

    schema_data: dict[str, Any] = get_default_es_index_schema(mapping)
    response = httpx.request(method, url, headers=headers, json=schema_data)

    if response.status_code == 200:
        logger.info(f"Elasticsearch index '{mapping.es_index}' created successfully.")
    elif response.status_code == 400:
        logger.info(f"Elasticsearch index '{mapping.es_index}' already exists.")
    else:
        logger.error(
            f"Failed to create Elasticsearch index '{mapping.es_index}'. Status code: {response.status_code}, Response: {response.text}"
        )


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def get_current_es_index_schema(mapping: Mapping) -> str:
    url = f"http://{ES_HOST}:{ES_PORT}/{mapping.es_index}"
    method = "GET"
    headers = {"Content-Type": "application/json"}

    response = httpx.request(method, url, headers=headers)

    if response.status_code == 200:
        data = response.json().get(mapping.es_index, {}).get("mappings", {})
    else:
        logger.error(
            f"Failed to get Elasticsearch index '{mapping.es_index}'. "
            f"Status code: {response.status_code}, Response: {response.text}"
        )
        data = {}
    return json.dumps(data, sort_keys=True)


def is_es_index_schema_mappings_valid(mapping: Mapping) -> bool:
    """
    Validate if the current Elasticsearch index schema mappings match the desired default schema.

    This function compares the current schema mappings with the default schema mappings
    by converting both to JSON strings with sorted keys and checking for equality.

    Args:
        mapping (Mapping): The mapping object containing the index name and schema file.

    Returns:
        bool: True if the current schema mappings match the default schema mappings,
            False otherwise.

    Note:
        The comparison is performed by serializing both mappings to JSON strings with
        sorted keys to ensure consistent ordering before comparison.
    """
    current_schema: str = get_current_es_index_schema(mapping)

    desired_schema: str = json.dumps(
        get_default_es_index_schema(mapping).get("mappings", {}),
        sort_keys=True,
    )

    return current_schema == desired_schema


def es_setup() -> bool:
    """
    Set up the Elasticsearch index by validating and recreating it if necessary.

    This function performs the following steps:
    1. Retrieves the current Elasticsearch index schema mappings
    2. Validates the current schema against the expected schema defined in
    3. If the schema is invalid or missing, removes the existing index if it exists and creates a new one
    4. If the schema is valid, no action is taken

    The function logs informational messages at each step of the process.

    Returns:
        bool: True if a new index was created, False if the existing index was valid.

    Raises:
        Any exceptions raised by the called functions (get_current_es_index_schema_mappings,
        is_es_index_schema_mappings_valid, remove_es_index, create_es_index) will propagate
        to the caller.
    """

    logger.info("Setting up Elasticsearch index...")

    new_index_created = False

    for mapping in MAPPINGS:
        if not is_es_index_schema_mappings_valid(mapping):
            logger.info(
                f"Elasticsearch index schema {mapping.es_index} is invalid. Recreating index..."
            )
            remove_es_index(mapping)
            create_es_index(mapping)
            new_index_created = True
        else:
            logger.info(
                f"Elasticsearch index schema {mapping.es_index} is valid. No action needed."
            )

    logger.info("Elasticsearch indexes setup completed.")
    return new_index_created
