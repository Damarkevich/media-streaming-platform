from logging import config as logging_config

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    project_name: str = "auth_service"
    project_description: str = (
        "Authentication service for the Movies Streaming Platform"
    )

    authjwt_secret_key: str = "your_secret_key_more_than_32_characters_long"
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
    postgres_password: str = "password"
    postgres_db_schema: str = "auth"

    sql_host: str = "localhost"
    sql_port: int = 6543
    sql_options: str = "-c search_path=auth,public"
    sql_echo: bool = False


settings = Settings()
