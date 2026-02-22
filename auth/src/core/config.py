from logging import config as logging_config

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    project_name: str = "auth_service"

    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    postgres_user: str = "app"
    postgres_password: str = "123qwe"
    postgres_db: str = "auth_database"
    postgres_db_schema: str = "auth"

    sql_host: str = "localhost"
    sql_port: int = 6543
    sql_options: str = "-c search_path=auth,public"


settings = Settings()
