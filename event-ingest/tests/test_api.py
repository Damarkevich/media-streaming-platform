import api.v1.events as events_api


def test_requires_jwt(client, producer) -> None:
    response = client.post("/api/v1/events/", json={"events": []})

    assert response.status_code == 401
    assert producer.sent_messages == []


def test_delegates_to_service_and_returns_its_error(
    client, producer, auth_headers, monkeypatch
) -> None:
    captured = {}

    def fake_process_event_batch(data, user_id, kafka_producer):
        captured["data"] = data
        captured["user_id"] = user_id
        captured["kafka_producer"] = kafka_producer
        return {"message": "forced validation error"}, 400

    monkeypatch.setattr(events_api, "process_event_batch", fake_process_event_batch)

    response = client.post(
        "/api/v1/events/",
        headers=auth_headers,
        json={"events": [{"raw": "value"}]},
    )

    assert response.status_code == 400
    assert response.get_json() == {"message": "forced validation error"}
    assert producer.sent_messages == []
    assert captured["data"] == {"events": [{"raw": "value"}]}
    assert captured["user_id"] == "user-123"
    assert captured["kafka_producer"] is producer


def test_delegates_to_service_and_returns_its_success(
    client, producer, auth_headers, monkeypatch
) -> None:
    def fake_process_event_batch(data, user_id, kafka_producer):
        return {
            "status": "success",
            "events_accepted": 7,
            "events_rejected": 2,
        }, 200

    monkeypatch.setattr(events_api, "process_event_batch", fake_process_event_batch)

    response = client.post(
        "/api/v1/events/",
        headers=auth_headers,
        json={"events": [{"any": "shape"}]},
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "success",
        "events_accepted": 7,
        "events_rejected": 2,
    }
    assert producer.sent_messages == []
