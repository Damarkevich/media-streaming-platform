from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict

from tests.functional.testdata.es_mapping import ES_MAPPING


class TestSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_file=".env")

    es_host: str = "test-elasticsearch"
    es_port: int = 9200
    es_schema: str = "http://"
    es_index: str = "movies"

    redis_host: str = "test-redis"
    redis_port: int = 6379

    service_url: str = "http://test-fastapi:8000"

    @property
    def es_url(self) -> str:
        return f"{self.es_schema}{self.es_host}:{self.es_port}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def es_index_mapping(self) -> dict[str, Any]:
        return ES_MAPPING


test_settings = TestSettings()
