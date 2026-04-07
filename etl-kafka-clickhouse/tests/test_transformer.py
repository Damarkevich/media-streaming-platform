from datetime import datetime
from uuid import UUID

from transformer import Transformer


def _valid_event() -> dict[str, object]:
    return {
        "event_id": "8b6c7ad2-7a5f-4d90-96d3-a8d5f1f67fb8",
        "user_id": "f56dc040-b6c0-46b0-b4f3-258742d7f683",
        "session_id": "cb021379-5149-4531-9e50-f72d1377a6f8",
        "event_type": "movie_start",
        "event_timestamp": 1712345678,
        "server_timestamp": "2024-04-06T10:00:00",
        "context": {"platform": "web"},
        "payload": {"movie_id": "08fd97f8-e47e-42cf-b6a0-d0f54818651f"},
    }


def test_transform_keeps_valid_event() -> None:
    transformer = Transformer()

    result = transformer.transform([_valid_event()])

    assert len(result) == 1
    row = result[0]
    assert row["event_type"] == "movie_start"
    assert isinstance(row["event_timestamp"], datetime)
    assert isinstance(row["server_timestamp"], datetime)
    assert row["movie_id"] == UUID("08fd97f8-e47e-42cf-b6a0-d0f54818651f")


def test_transform_skips_invalid_event() -> None:
    transformer = Transformer()

    invalid_event = _valid_event()
    invalid_event["event_id"] = "not-a-uuid"

    result = transformer.transform([invalid_event])

    assert result == []


def test_transform_allows_invalid_optional_movie_id() -> None:
    transformer = Transformer()

    event = _valid_event()
    event["payload"] = {"movie_id": "bad-id"}

    result = transformer.transform([event])

    assert len(result) == 1
    assert result[0]["movie_id"] is None


def test_transform_accepts_datetime_values() -> None:
    transformer = Transformer()

    event = _valid_event()
    event["event_timestamp"] = datetime(2024, 4, 6, 10, 0, 0)
    event["server_timestamp"] = datetime(2024, 4, 6, 10, 0, 1)

    result = transformer.transform([event])

    assert len(result) == 1
    assert isinstance(result[0]["event_timestamp"], datetime)
    assert isinstance(result[0]["server_timestamp"], datetime)
