import logging
from datetime import datetime

import redis
from config.etl_mappings import MAPPINGS
from config.settings import DEFAULT_TIMESTAMP, REDIS_DB, REDIS_HOST, REDIS_PORT
from state import RedisStorage, State

logger = logging.getLogger(__name__)


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

    for mapping in MAPPINGS:
        value = state.get_state(mapping.postgres_table)

        try:
            datetime.fromisoformat(value)
        except (ValueError, AttributeError, TypeError):
            state.set_state(mapping.postgres_table, DEFAULT_TIMESTAMP)


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
