import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class BaseStorage(Protocol):
    """Base storage protocol for state persistence.

    This protocol defines the interface for state storage implementations.
    Any class implementing this protocol must provide methods to save and
    retrieve state data.

    Methods
    -------
    save_state(state: dict[str, Any]) -> None
        Save the current state to storage.

        Parameters
        ----------
        state : dict[str, Any]
            Dictionary containing state data to be persisted.

    retrieve_state() -> dict[str, Any]
        Retrieve the previously saved state from storage.

        Returns
        -------
        dict[str, Any]
            Dictionary containing the retrieved state data.
    """

    def save_state(self, state: dict[str, Any]) -> None: ...

    def retrieve_state(self) -> dict[str, Any]: ...


class JsonFileStorage:
    """
    A storage class that persists state to a JSON file.

    This class provides methods to save and retrieve state information using a JSON file
    as the storage backend. It automatically initializes the file if it doesn't exist or
    is invalid.

    Attributes:
        file_path (str): The path to the JSON file used for storage.

    Methods:
        save_state(state: dict[str, Any]) -> None:
            Saves the given state dictionary to the JSON file. If state already exists,
            it merges the new state with the existing one.

        retrieve_state() -> dict[str, Any]:
            Retrieves and returns the current state from the JSON file.

    Example:
        >>> storage = JsonFileStorage("state.json")
        >>> storage.save_state({"last_updated": "2023-01-01"})
        >>> state = storage.retrieve_state()
        >>> print(state)
        {'last_updated': '2023-01-01'}
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._initialize_file()

    def _initialize_file(self) -> None:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info(
                f"File {self.file_path} not found or invalid. Creating a new one."
            )
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def save_state(self, state: dict[str, Any]) -> None:
        current_state = self.retrieve_state()
        current_state.update(state)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(current_state, f)

    def retrieve_state(self) -> dict[str, Any]:
        with open(self.file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
            return state


class RedisStorage:
    """
    A storage class that persists state data in Redis.

    This class provides methods to save and retrieve state information using Redis
    as the backend storage. State is stored as a JSON-serialized dictionary.

    Attributes:
        redis_client: A Redis client instance used for data persistence.
        key (str): The Redis key under which state data is stored. Defaults to "data".

    Methods:
        save_state(state: dict[str, Any]) -> None:
            Merges the provided state dictionary with existing state and saves it to Redis.

        retrieve_state() -> dict[str, Any]:
            Retrieves the current state from Redis. Returns an empty dictionary if no state exists.

    Example:
        >>> import redis
        >>> r = redis.Redis(host='localhost', port=6379, db=0)
        >>> storage = RedisStorage(r)
        >>> storage.save_state({"last_updated": "2023-01-01"})
        >>> state = storage.retrieve_state()
        >>> print(state)
        {'last_updated': '2023-01-01'}
    """

    def __init__(
        self, redis_client, key: str = "data", recreate_state: bool = False
    ) -> None:
        self.redis_client = redis_client
        self.key = key

        if recreate_state:
            self.redis_client.delete(self.key)

    def save_state(self, state: dict[str, Any]) -> None:
        current_state = self.retrieve_state()
        current_state.update(state)
        state_json = json.dumps(current_state)
        self.redis_client.set(self.key, state_json)

    def retrieve_state(self) -> dict[str, Any]:
        state_json = self.redis_client.get(self.key)
        if state_json is None:
            return {}
        return json.loads(state_json)


class State:
    """
    A class for managing application state using a storage backend.

    This class provides a simple interface for storing and retrieving state information
    using a pluggable storage mechanism.

    Attributes:
        storage (BaseStorage): The storage backend used for persisting state data.

    Methods:
        set_state(key: str, value: Any) -> None:
            Stores a state value associated with the given key.

            Args:
                key (str): The key to identify the state value.
                value (Any): The value to store.

        get_state(key: str) -> Any:
            Retrieves a state value associated with the given key.

            Args:
                key (str): The key to identify the state value.

            Returns:
                Any: The stored value associated with the key, or None if the key doesn't exist.
    """

    def __init__(self, storage: BaseStorage) -> None:
        self.storage = storage

    def set_state(self, key: str, value: Any) -> None:
        self.storage.save_state({key: value})

    def get_state(self, key: str) -> Any:
        return self.storage.retrieve_state().get(key)
