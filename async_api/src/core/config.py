from logging import config as logging_config

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    development_mode: bool = False

    service_name: str = "content_service"
    service_description: str = "Content service for the Movies Streaming Platform"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    cache_expire_in_seconds: int = 300
    es_schema: str = "http://"
    es_host: str = "localhost"
    es_port: int = 9200

    otel_traces_endpoint: str = "http://localhost:4318/v1/traces"
    otel_console_export_enabled: bool = False

    sentry_dsn: str = ""

    authjwt_secret_key: str
    authjwt_algorithm: str = "HS256"

    subscriber_role_name: str = "subscriber"
    admin_role_name: str = "admin"

    @field_validator("authjwt_secret_key")
    @classmethod
    def validate_authjwt_secret_key(cls, value: str) -> str:
        """Ensure that AUTHJWT_SECRET_KEY is set and meets the minimum length requirement."""
        if len(value.strip()) < 32:
            msg = "AUTHJWT_SECRET_KEY should be at least 32 characters for security"
            raise ValueError(msg)
        return value


settings = Settings()  # pyright: ignore[reportCallIssue]
