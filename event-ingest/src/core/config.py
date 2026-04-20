from logging import config as logging_config

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    event_ingest_service_name: str = "Event Ingest Service"
    event_ingest_service_description: str = (
        "Event Ingest service for the Movies Streaming Platform"
    )
    event_ingest_max_content_length: int = 1 * 1024 * 1024  # 1 MB

    debug: bool = False

    authjwt_secret_key: str
    authjwt_algorithm: str = "HS256"

    kafka_bootstrap_servers: list[str] = ["localhost:9094"]
    kafka_api_version: tuple[int, int] = (3, 4)
    kafka_acks: str = "all"
    kafka_retries: int = 3
    kafka_request_timeout_ms: int = 30000
    kafka_topic: str = "events"

    sentry_dsn: str = ""

    @field_validator("authjwt_secret_key")
    @classmethod
    def validate_authjwt_secret_key(cls, value: str) -> str:
        """Ensure that AUTHJWT_SECRET_KEY is set and meets the minimum length requirement."""
        if len(value.strip()) < 32:
            raise ValueError(
                "AUTHJWT_SECRET_KEY should be at least 32 characters for security"
            )
        return value


settings = Settings()
