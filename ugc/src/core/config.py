from logging import config as logging_config

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    development_mode: bool = False

    service_name: str = "ugc_service"
    service_description: str = (
        "User-Generated Content service for the Movies Streaming Platform"
    )

    # MongoDB
    mongodb_host: str = "127.0.0.1"
    mongodb_port: int = 27017
    mongodb_database: str = "ugc_database"
    mongodb_root_username: str = "mongo"
    mongodb_root_password: str = "mongo_password"
    mongodb_replica_set: str | None = "rs0"

    # Redis (for JWT denylist)
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    # JWT (shared with auth service)
    authjwt_secret_key: str
    authjwt_algorithm: str = "HS256"

    subscriber_role_name: str = "subscriber"
    admin_role_name: str = "admin"

    # Tracing
    otel_traces_endpoint: str = "http://localhost:4318/v1/traces"
    otel_console_export_enabled: bool = False

    sentry_dsn: str = ""

    @field_validator("authjwt_secret_key")
    @classmethod
    def validate_authjwt_secret_key(cls, value: str) -> str:
        if len(value.strip()) < 32:
            raise ValueError(
                "AUTHJWT_SECRET_KEY should be at least 32 characters for security"
            )
        return value

    @property
    def mongodb_uri(self) -> str:
        uri = (
            f"mongodb://{self.mongodb_root_username}:{self.mongodb_root_password}"
            f"@{self.mongodb_host}:{self.mongodb_port}"
            f"/{self.mongodb_database}?authSource=admin"
        )
        if self.mongodb_replica_set:
            uri = f"{uri}&replicaSet={self.mongodb_replica_set}"
        return uri


settings = Settings()
