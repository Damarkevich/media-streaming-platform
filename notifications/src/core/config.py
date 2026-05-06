from logging import config as logging_config

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    development_mode: bool = False

    service_name: str = "notifications_service"
    service_description: str = "Notifications service for the Movies Streaming Platform"

    cors_origins: list[str] = ["http://localhost:3000"]

    # JWT — shared secret with auth service for token validation
    authjwt_secret_key: str
    authjwt_token_location: set[str] = {"headers"}
    authjwt_header_name: str = "Authorization"
    authjwt_header_type: str = "Bearer"

    postgres_db: str = "movies_database"
    postgres_user: str = "app"
    postgres_password: str
    postgres_db_schema: str = "notif"

    sql_host: str = "localhost"
    sql_port: int = 5432
    sql_echo: bool = False

    # Internal service-to-service auth key (not exposed via nginx)
    internal_api_key: str = ""

    # Auth service base URL for internal user listing
    auth_internal_url: str = "http://movies-auth:8000"

    # Kafka
    kafka_bootstrap_servers: str = "kafka-0:9092,kafka-1:9092,kafka-2:9092"

    sentry_dsn: str = ""
    otel_traces_endpoint: str = "http://localhost:4318/v1/traces"
    otel_console_export_enabled: bool = False


settings = Settings()
