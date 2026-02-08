from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


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
        return {
            "settings": {
                "refresh_interval": "1s",
                "analysis": {
                    "filter": {
                        "english_stop": {"type": "stop", "stopwords": "_english_"},
                        "english_stemmer": {"type": "stemmer", "language": "english"},
                        "english_possessive_stemmer": {
                            "type": "stemmer",
                            "language": "possessive_english",
                        },
                        "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                        "russian_stemmer": {"type": "stemmer", "language": "russian"},
                    },
                    "analyzer": {
                        "ru_en": {
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "english_stop",
                                "english_stemmer",
                                "english_possessive_stemmer",
                                "russian_stop",
                                "russian_stemmer",
                            ],
                        }
                    },
                },
            },
            "mappings": {
                "dynamic": "strict",
                "properties": {
                    "id": {"type": "keyword"},
                    "imdb_rating": {"type": "float"},
                    "title": {
                        "type": "text",
                        "analyzer": "ru_en",
                        "fields": {"raw": {"type": "keyword"}},
                    },
                    "description": {"type": "text", "analyzer": "ru_en"},
                    "directors_names": {"type": "text", "analyzer": "ru_en"},
                    "actors_names": {"type": "text", "analyzer": "ru_en"},
                    "writers_names": {"type": "text", "analyzer": "ru_en"},
                    "genres_names": {"type": "text", "analyzer": "ru_en"},
                    "genres": {
                        "type": "nested",
                        "dynamic": "strict",
                        "properties": {
                            "id": {"type": "keyword"},
                            "name": {"type": "text", "analyzer": "ru_en"},
                        },
                    },
                    "directors": {
                        "type": "nested",
                        "dynamic": "strict",
                        "properties": {
                            "id": {"type": "keyword"},
                            "full_name": {"type": "text", "analyzer": "ru_en"},
                        },
                    },
                    "actors": {
                        "type": "nested",
                        "dynamic": "strict",
                        "properties": {
                            "id": {"type": "keyword"},
                            "full_name": {"type": "text", "analyzer": "ru_en"},
                        },
                    },
                    "writers": {
                        "type": "nested",
                        "dynamic": "strict",
                        "properties": {
                            "id": {"type": "keyword"},
                            "full_name": {"type": "text", "analyzer": "ru_en"},
                        },
                    },
                },
            },
        }


test_settings = TestSettings()
