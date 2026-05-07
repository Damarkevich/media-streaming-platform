from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    # Kafka
    kafka_bootstrap_servers: str = "kafka-0:9092,kafka-1:9092,kafka-2:9092"
    kafka_consumer_group: str = "delivery-worker"

    # PostgreSQL (notif schema)
    postgres_db: str = "movies_database"
    postgres_user: str = "app"
    postgres_password: str
    sql_host: str = "movies-db"
    sql_port: int = 5432
    sql_echo: bool = False
    postgres_db_schema: str = "notif"

    # Redis (throttle)
    redis_host: str = "movies-redis"
    redis_port: int = 6379
    review_liked_throttle_ttl: int = 86400  # seconds (1 day per author)

    # Brevo
    brevo_api_key: str
    brevo_sender_email: str = "noreply@movies-platform.com"
    brevo_sender_name: str = "Movies Platform"

    # Auth internal
    auth_internal_url: str = "http://movies-auth:8000"
    internal_api_key: str = ""

    # Consumer retry behavior
    consumer_max_retries: int = 3
    consumer_retry_delay_seconds: float = 1.0


settings = Settings()
