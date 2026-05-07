from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    # Kafka
    kafka_bootstrap_servers: str = "kafka-0:9092,kafka-1:9092,kafka-2:9092"

    # PostgreSQL (notif schema — read cron expression + template)
    postgres_db: str = "movies_database"
    postgres_user: str = "app"
    postgres_password: str
    sql_host: str = "movies-db"
    sql_port: int = 5432
    sql_echo: bool = False

    # Auth internal
    auth_internal_url: str = "http://movies-auth:8000"
    internal_api_key: str = ""

    # Async API (movies list)
    async_api_url: str = "http://movies-async-api:8000"

    # Weekly digest
    weekly_digest_top_n: int = 10
    # Fallback cron if not in DB — every Friday 09:00
    weekly_digest_cron: str = "0 9 * * 5"

    # Campaign fan-out polling (processes notif.campaigns in QUEUED status)
    campaign_fanout_poll_seconds: int = 15
    campaign_fanout_batch_size: int = 10


settings = Settings()
