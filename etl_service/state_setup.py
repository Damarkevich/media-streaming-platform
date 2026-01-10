import os
from datetime import datetime

import redis
from dotenv import load_dotenv

from logger import logger
from state import RedisStorage, State
from table_names import TableNames

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
DEFAULT_TIMESTAMP = "0001-01-01T00:00:00.000000+00:00"


def set_default_modification_data(state: State) -> None:
    """
    Initialize modification data timestamps in state if they are invalid or missing.

    This function validates the modification timestamps for person, film_work, and genre
    entities stored in the state. If any timestamp is invalid (cannot be parsed as ISO format)
    or missing (TypeError), it sets that timestamp to the DEFAULT_TIMESTAMP value.

    Args:
        state (State): The state object that stores and retrieves modification timestamps.

    Raises:
        None: All exceptions are caught and handled internally by setting default values.

    Note:
        - Expects timestamps in ISO format
        - Uses DEFAULT_TIMESTAMP constant when resetting invalid or missing timestamps
    """

    for key in TableNames:
        value = state.get_state(key.value)

        try:
            datetime.fromisoformat(value)
        except (ValueError, AttributeError, TypeError):
            state.set_state(key.value, DEFAULT_TIMESTAMP)


def state_setup(recreate_state: bool = False) -> State:
    """
    Initialize the state storage.

    Args:
        recreate_state (bool): If True, the state storage will be recreated/reset.

    Returns:
        State: An instance of the State class with the initialized storage.
    """
    logger.info("Initializing state storage...")
    storage = RedisStorage(
        redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT), db=int(REDIS_DB)),
        key="etl_state",
        recreate_state=recreate_state,
    )
    state = State(storage)

    set_default_modification_data(state)
    return state
