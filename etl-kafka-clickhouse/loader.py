import logging
import time
from typing import Any

from clickhouse_driver import Client

from config.settings import settings

logger = logging.getLogger(__name__)

INSERT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "user_id",
    "session_id",
    "event_type",
    "event_timestamp",
    "server_timestamp",
    "context",
    "payload",
    "movie_id",
)


class ClickHouseLoader:
    """Load transformed rows into the distributed ClickHouse table."""

    def __init__(self) -> None:
        """Initialize ClickHouse client and target table names."""
        self.database = settings.clickhouse_database
        self.table = settings.clickhouse_table
        self.distributed_table = self.database + "." + self.table
        self.insert_target_table = self.distributed_table

        self.client = Client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )

        logger.info(
            "ClickHouse loader started. insert_target=%s",
            self.insert_target_table,
        )

    def load(self, events: list[dict[str, Any]]) -> None:
        """Insert a batch of transformed events into ClickHouse."""
        if not events:
            return

        rows = [tuple(event[column] for column in INSERT_COLUMNS) for event in events]
        columns_sql = ", ".join(INSERT_COLUMNS)
        query = "INSERT INTO {table} ({columns}) VALUES".format(
            table=self.insert_target_table,
            columns=columns_sql,
        )

        self.client.execute(query, rows)

    def load_with_retry(self, events: list[dict[str, Any]]) -> None:
        """Insert with retry and exponential backoff on transient failures."""
        attempts = settings.clickhouse_insert_max_retries + 1

        for attempt in range(1, attempts + 1):
            try:
                self.load(events)
                return
            except Exception:
                if attempt >= attempts:
                    raise

                backoff = settings.clickhouse_insert_retry_backoff_seconds * (
                    2 ** (attempt - 1)
                )
                logger.exception(
                    "ClickHouse load failed on attempt %s/%s. Retrying in %.2fs.",
                    attempt,
                    attempts,
                    backoff,
                )
                time.sleep(backoff)

    def close(self) -> None:
        """Close the ClickHouse client connection."""
        self.client.disconnect_connection()
