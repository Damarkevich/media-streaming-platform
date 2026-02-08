from logging import config as logging_config

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.logger import LOGGING

logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    project_name: str = "movies"
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    cache_expire_in_seconds: int = 300
    es_schema: str = "http://"
    es_host: str = "localhost"
    es_port: int = 9200


settings = Settings()
