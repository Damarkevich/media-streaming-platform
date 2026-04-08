from uuid import uuid4

import pytest
from marshmallow import ValidationError

from schemas import EventApiSchema, EventBatchSchema


def _event_payload(**overrides: object) -> dict[str, object]:
    payload = {
        "event_id": str(uuid4()),
        "event_type": "page_view",
        "event_timestamp": 1_744_000_000,
        "session_id": str(uuid4()),
        "context": {"device": "mobile"},
        "payload": {"page": "/movies"},
    }
    payload.update(overrides)
    return payload


def test_loads_valid_event() -> None:
    schema = EventApiSchema()

    event = schema.load(_event_payload())

    assert event["event_type"] == "page_view"
    assert event["context"]["device"] == "mobile"


def test_rejects_unknown_event_type() -> None:
    schema = EventApiSchema()

    with pytest.raises(ValidationError):
        schema.load(_event_payload(event_type="not_supported"))


def test_loads_valid_event_batch() -> None:
    schema = EventBatchSchema()

    batch = schema.load({"events": [_event_payload()]})

    assert isinstance(batch["events"], list)
    assert len(batch["events"]) == 1


def test_rejects_event_batch_without_events_key() -> None:
    schema = EventBatchSchema()

    with pytest.raises(ValidationError):
        schema.load({})


def test_rejects_event_batch_with_non_list_events() -> None:
    schema = EventBatchSchema()

    with pytest.raises(ValidationError):
        schema.load({"events": {"event_type": "page_view"}})
