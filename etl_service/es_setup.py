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
ES_SCHEMA_FILE = os.getenv("ES_SCHEMA_FILE", "es_schema.json")


def get_default_es_index_schema() -> dict[str, Any]:
    """
    Load and return the default Elasticsearch index schema from a JSON file.

    This function reads the Elasticsearch index schema configuration from a predefined
    JSON file (ES_SCHEMA_FILE) and returns it as a dictionary.

    Returns:
        dict: A dictionary containing the Elasticsearch index schema configuration,
              including mappings, settings, and other index-related properties.

    Raises:
        FileNotFoundError: If the ES_SCHEMA_FILE does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
        IOError: If there are issues reading the file.

    Example:
        >>> schema = get_default_es_index_schema()
        >>> print(schema.keys())
        dict_keys(['settings', 'mappings'])
    """
    with open(ES_SCHEMA_FILE, "r") as f:
        return json.load(f)


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def remove_es_index() -> None:
    """
    Remove an Elasticsearch index.

    Sends a DELETE request to remove the specified Elasticsearch index. Logs the outcome
    of the operation based on the HTTP response status code.

    Returns:
        None

    Raises:
        No exceptions are raised explicitly, but HTTP errors are logged.

    Note:
        - If the index is successfully removed (status 200), an info message is logged.
        - If the index does not exist (status 404), an info message is logged.
        - For any other status code, an error message with details is logged.
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_SCHEMA_NAME}"
    method = "DELETE"
    headers = {"Content-Type": "application/json"}

    response = httpx.request(method, url, headers=headers)

    if response.status_code == 200:
        logger.info(f"Elasticsearch index '{ES_SCHEMA_NAME}' removed successfully.")
    elif response.status_code == 404:
        logger.info(f"Elasticsearch index '{ES_SCHEMA_NAME}' does not exist.")
    else:
        logger.error(
            f"Failed to remove Elasticsearch index '{ES_SCHEMA_NAME}'. Status code: {response.status_code}, Response: {response.text}"
        )


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def create_es_index() -> None:
    """
    Create an Elasticsearch index with the default schema.

    This function sends a PUT request to create a new Elasticsearch index using
    the schema retrieved from get_default_es_index_schema(). It handles different
    response scenarios:
    - 200: Index created successfully
    - 400: Index already exists
    - Other: Logs an error with the status code and response text

    Raises:
        httpx.RequestError: If the HTTP request fails due to network or connection issues.

    Returns:
        None
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_SCHEMA_NAME}"
    method = "PUT"
    headers = {"Content-Type": "application/json"}

    schema_data: dict[str, Any] = get_default_es_index_schema()

    response = httpx.request(method, url, headers=headers, json=schema_data)

    if response.status_code == 200:
        logger.info(f"Elasticsearch index '{ES_SCHEMA_NAME}' created successfully.")
    elif response.status_code == 400:
        logger.info(f"Elasticsearch index '{ES_SCHEMA_NAME}' already exists.")
    else:
        logger.error(
            f"Failed to create Elasticsearch index '{ES_SCHEMA_NAME}'. Status code: {response.status_code}, Response: {response.text}"
        )


@backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
def get_current_es_index_schema_mappings() -> dict[str, Any]:
    """
    Retrieve the current mappings schema from an Elasticsearch index.

    This function sends a GET request to the Elasticsearch server to fetch the
    mappings (field definitions and data types) of the specified index.

    Returns:
        dict[str, Any]: A dictionary containing the mappings of the Elasticsearch
                        index. Returns an empty dictionary if the request fails or
                        if the index does not exist.

    Raises:
        No exceptions are raised directly, but HTTP errors are logged via logger.error.

    Note:
        - Uses global variables ES_HOST, ES_PORT, and ES_SCHEMA_NAME for connection details.
        - Logs an error message if the request fails (status code != 200).
    """
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_SCHEMA_NAME}"
    method = "GET"
    headers = {"Content-Type": "application/json"}

    response = httpx.request(method, url, headers=headers)

    if response.status_code == 200:
        return response.json().get(ES_SCHEMA_NAME, {}).get("mappings", {})
    else:
        logger.error(
            f"Failed to get Elasticsearch index '{ES_SCHEMA_NAME}'. Status code: {response.status_code}, Response: {response.text}"
        )
        return {}


def is_es_index_schema_mappings_valid(current_schema_mappings: dict[str, Any]) -> bool:
    """
    Validate if the current Elasticsearch index schema mappings match the desired default schema.

    This function compares the current schema mappings with the default schema mappings
    by converting both to JSON strings with sorted keys and checking for equality.

    Args:
        current_schema_mappings (dict[str, Any]): The current schema mappings from an
            Elasticsearch index to validate.

    Returns:
        bool: True if the current schema mappings match the default schema mappings,
            False otherwise.

    Note:
        The comparison is performed by serializing both mappings to JSON strings with
        sorted keys to ensure consistent ordering before comparison.
    """
    current_schema_mappings_json: str = json.dumps(
        current_schema_mappings,
        sort_keys=True,
    )
    desired_schema_mappings_json: str = json.dumps(
        get_default_es_index_schema().get("mappings", {}),
        sort_keys=True,
    )

    return current_schema_mappings_json == desired_schema_mappings_json


def es_setup() -> bool:
    """
    Set up the Elasticsearch index by validating and recreating it if necessary.

    This function performs the following steps:
    1. Retrieves the current Elasticsearch index schema mappings
    2. Validates the current schema against the expected schema defined in ES_SCHEMA_FILE
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

    current_schema_mappings: dict = get_current_es_index_schema_mappings()

    new_index_created = False

    if not is_es_index_schema_mappings_valid(current_schema_mappings):
        logger.info("Elasticsearch index schema is invalid. Recreating index...")
        remove_es_index()
        create_es_index()
        new_index_created = True
    else:
        logger.info("Elasticsearch index schema is valid. No action needed.")

    logger.info("Elasticsearch index setup completed.")
    return new_index_created