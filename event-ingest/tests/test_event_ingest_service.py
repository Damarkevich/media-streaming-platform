import json

from services.event_ingest import process_event_batch


def test_process_event_batch_returns_400_for_empty_payload(producer) -> None:
    response_body, status_code = process_event_batch(None, "user-123", producer)

    assert status_code == 400
    assert response_body == {"details": {"_schema": ["No input data provided"]}}
    assert producer.sent_messages == []


def test_process_event_batch_returns_400_for_non_dict_payload(producer) -> None:
    response_body, status_code = process_event_batch(
        ["unexpected"], "user-123", producer
    )

    assert status_code == 400
    assert response_body == {
        "details": {"_schema": ["Invalid input type."]},
    }
    assert producer.sent_messages == []


def test_process_event_batch_returns_400_when_events_not_list(producer) -> None:
    response_body, status_code = process_event_batch(
        {"events": {"event_type": "page_view"}},
        "user-123",
        producer,
    )

    assert status_code == 400
    assert response_body == {
        "details": {"events": ["'events' key should be a list"]},
    }
    assert producer.sent_messages == []


def test_process_event_batch_sends_valid_event(producer, make_event) -> None:
    response_body, status_code = process_event_batch(
        {"events": [make_event()]},
        "user-123",
        producer,
    )

    assert status_code == 200
    assert response_body == {
        "status": "success",
        "events_accepted": 1,
        "events_rejected": 0,
    }
    assert len(producer.sent_messages) == 1

    sent_message = producer.sent_messages[0]
    assert sent_message["key"] == b"user-123"

    payload = json.loads(sent_message["value"].decode("utf-8"))
    assert payload["user_id"] == "user-123"
    assert payload["event_type"] == "page_view"
    assert "server_timestamp" in payload


def test_process_event_batch_accepts_valid_and_rejects_invalid_events(
    producer, make_event
) -> None:
    response_body, status_code = process_event_batch(
        {
            "events": [
                make_event(),
                make_event(event_type="invalid_type"),
            ]
        },
        "user-123",
        producer,
    )

    assert status_code == 200
    assert response_body == {
        "status": "success",
        "events_accepted": 1,
        "events_rejected": 1,
    }
    assert len(producer.sent_messages) == 1


def test_process_event_batch_returns_503_when_kafka_delivery_fails(
    producer, make_event
) -> None:
    producer.delivery_error = RuntimeError("kafka unavailable")

    response_body, status_code = process_event_batch(
        {"events": [make_event()]},
        "user-123",
        producer,
    )

    assert status_code == 503
    assert response_body == {
        "status": "partial_failure",
        "details": "Some events failed to deliver to Kafka",
        "events_accepted": 0,
        "events_rejected": 1,
    }
