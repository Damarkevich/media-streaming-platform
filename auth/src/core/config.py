from logging import config as logging_config

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    development_mode: bool = False

    service_name: str = "auth_service"
    service_description: str = (
        "Authentication service for the Movies Streaming Platform"
    )

    cors_origins: list[str] = ["http://localhost:3000"]

    authjwt_secret_key: str
    authjwt_token_location: set[str] = {"headers"}
    authjwt_header_name: str = "Authorization"
    authjwt_header_type: str = "Bearer"
    authjwt_denylist_enabled: bool = True
    authjwt_denylist_token_checks: set[str] = {"access", "refresh"}
    access_token_expires: int = 60 * 5  # 5 minutes in seconds
    refresh_token_expires: int = 60 * 60 * 24 * 7  # 7 days in seconds

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    permissions_cache_ttl: int = 60

    postgres_db: str = "auth_database"
    postgres_user: str = "app"
    postgres_password: str
    postgres_db_schema: str = "auth"

    sql_host: str = "localhost"
    sql_port: int = 6543
    sql_options: str = "-c search_path=auth,public"
    sql_echo: bool = False

    otel_traces_endpoint: str = "http://localhost:4318/v1/traces"
    otel_console_export_enabled: bool = False

    @field_validator("authjwt_secret_key")
    @classmethod
    def validate_authjwt_secret_key(cls, value: str) -> str:
        """Ensure that AUTHJWT_SECRET_KEY is set and meets the minimum length requirement."""
        if len(value.strip()) < 32:
            raise ValueError(
                "AUTHJWT_SECRET_KEY should be at least 32 characters for security"
            )
        return value


settings = Settings()  # type: ignore
