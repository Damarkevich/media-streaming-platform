import pytest
from pydantic import ValidationError

from config.settings import Settings


BASE_CONFIG = {
    "CLICKHOUSE_DEFAULT_PASSWORD": "test-password",
}


def test_settings_accepts_valid_defaults() -> None:
    cfg = Settings(**BASE_CONFIG)

    assert cfg.clickhouse_database == "events"
    assert cfg.clickhouse_table == "user_events"
    assert cfg.clickhouse_sharding_key == "cityHash64(user_id)"


def test_settings_rejects_invalid_sql_identifier() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_CONFIG, clickhouse_table="bad-table")


def test_settings_rejects_invalid_sharding_key() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_CONFIG, clickhouse_sharding_key="rand()")


def test_settings_rejects_invalid_replicated_suffix() -> None:
    with pytest.raises(ValidationError):
        Settings(**BASE_CONFIG, clickhouse_replicated_path_suffix="bad-suffix")
