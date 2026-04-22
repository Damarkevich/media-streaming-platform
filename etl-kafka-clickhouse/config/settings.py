import re

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SHARDING_KEY_RE = re.compile(r"^cityHash64\([A-Za-z_][A-Za-z0-9_]*\)$")
PATH_SUFFIX_RE = re.compile(r"^[A-Za-z0-9_]+$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        populate_by_name=True,
    )

    log_level: str = Field(default="INFO", alias="ETL_KAFKA_CLICKHOUSE_LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        alias="ETL_KAFKA_CLICKHOUSE_LOG_FORMAT",
    )
    log_name: str = Field(
        default="etl_kafka_to_clickhouse", alias="ETL_KAFKA_CLICKHOUSE_LOG_NAME"
    )

    clickhouse_host: str = Field(default="localhost", alias="ETL_KAFKA_CLICKHOUSE_HOST")
    clickhouse_port: int = Field(default=9000, alias="ETL_KAFKA_CLICKHOUSE_PORT")
    clickhouse_user: str = Field(default="default", alias="CLICKHOUSE_DEFAULT_USER")
    clickhouse_password: str = Field(alias="CLICKHOUSE_DEFAULT_PASSWORD")
    clickhouse_database: str = Field(
        default="events", alias="ETL_KAFKA_CLICKHOUSE_DATABASE"
    )
    clickhouse_table: str = Field(
        default="user_events", alias="ETL_KAFKA_CLICKHOUSE_TABLE"
    )
    clickhouse_cluster_name: str = Field(
        default="company_cluster", alias="ETL_KAFKA_CLICKHOUSE_CLUSTER_NAME"
    )
    clickhouse_run_ddl_on_cluster: bool = Field(
        default=True, alias="ETL_KAFKA_CLICKHOUSE_RUN_DDL_ON_CLUSTER"
    )
    clickhouse_local_database: str = Field(
        default="shard", alias="ETL_KAFKA_CLICKHOUSE_LOCAL_DATABASE"
    )
    clickhouse_sharding_key: str = Field(
        default="cityHash64(user_id)", alias="ETL_KAFKA_CLICKHOUSE_SHARDING_KEY"
    )
    clickhouse_replicated_path_suffix: str = Field(
        default="v2", alias="ETL_KAFKA_CLICKHOUSE_REPLICATED_PATH_SUFFIX"
    )

    kafka_bootstrap_servers: list[str] = Field(
        default=["localhost:9094"],
        alias="KAFKA_BOOTSTRAP_SERVERS",
    )
    kafka_api_version: tuple[int, int] = Field(
        default=(3, 4), alias="KAFKA_API_VERSION"
    )
    kafka_topic: str = Field(default="events", alias="KAFKA_TOPIC")

    kafka_auto_offset_reset: str = Field(
        default="earliest", alias="ETL_KAFKA_CLICKHOUSE_AUTO_OFFSET_RESET"
    )
    kafka_group_id: str = Field(
        default="etl-kafka-clickhouse-group", alias="ETL_KAFKA_CLICKHOUSE_GROUP_ID"
    )
    kafka_max_batch_size: int = Field(
        default=100, alias="ETL_KAFKA_CLICKHOUSE_MAX_EXTRACT_BATCH_SIZE"
    )
    kafka_poll_timeout_ms: int = Field(
        default=1000, alias="ETL_KAFKA_CLICKHOUSE_POLL_TIMEOUT_MS"
    )
    clickhouse_min_batch_size: int = Field(
        default=1000, alias="ETL_KAFKA_CLICKHOUSE_MIN_LOAD_BATCH_SIZE"
    )
    etl_batch_max_wait_seconds: float = Field(
        default=5.0, alias="ETL_KAFKA_CLICKHOUSE_BATCH_MAX_WAIT_SECONDS"
    )
    etl_idle_sleep_seconds: float = Field(
        default=0.5, alias="ETL_KAFKA_CLICKHOUSE_IDLE_SLEEP_SECONDS"
    )
    clickhouse_insert_max_retries: int = Field(
        default=3, alias="ETL_KAFKA_CLICKHOUSE_INSERT_MAX_RETRIES"
    )
    clickhouse_insert_retry_backoff_seconds: float = Field(
        default=1.0, alias="ETL_KAFKA_CLICKHOUSE_INSERT_RETRY_BACKOFF_SECONDS"
    )

    @field_validator(
        "clickhouse_database",
        "clickhouse_table",
        "clickhouse_cluster_name",
        "clickhouse_local_database",
    )
    @classmethod
    def validate_sql_identifier(cls, value: str) -> str:
        if not SQL_IDENTIFIER_RE.fullmatch(value):
            msg = "Invalid SQL identifier"
            raise ValueError(msg)
        return value

    @field_validator("clickhouse_sharding_key")
    @classmethod
    def validate_sharding_key(cls, value: str) -> str:
        if not SHARDING_KEY_RE.fullmatch(value):
            msg = "Invalid sharding key. Expected format: cityHash64(column_name)"
            raise ValueError(msg)
        return value

    @field_validator("clickhouse_replicated_path_suffix")
    @classmethod
    def validate_replicated_path_suffix(cls, value: str) -> str:
        if not PATH_SUFFIX_RE.fullmatch(value):
            msg = "Invalid replicated path suffix"
            raise ValueError(msg)
        return value


settings = Settings()
