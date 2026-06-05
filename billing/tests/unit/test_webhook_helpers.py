from src.services.webhooks import _extract_object, _extract_refund_id, _resolve_event_id


def test_resolve_event_id_uses_event_id_when_present() -> None:
    event = {"id": "evt_123"}

    assert _resolve_event_id(event, "hash") == "evt_123"


def test_resolve_event_id_falls_back_to_payload_hash() -> None:
    event = {}

    assert _resolve_event_id(event, "hash") == "missing-id:hash"


def test_extract_object_returns_dict_object() -> None:
    event = {"data": {"object": {"id": "x"}}}

    assert _extract_object(event) == {"id": "x"}


def test_extract_object_returns_empty_dict_for_non_dict() -> None:
    event = {"data": {"object": "bad"}}

    assert _extract_object(event) == {}


def test_extract_refund_id_for_refund_updated() -> None:
    obj = {"id": "re_123"}

    assert _extract_refund_id("refund.updated", obj) == "re_123"


def test_extract_refund_id_for_charge_refunded() -> None:
    obj = {"refunds": {"data": [{"id": "re_456"}]}}

    assert _extract_refund_id("charge.refunded", obj) == "re_456"


def test_extract_refund_id_returns_none_for_unknown_payload() -> None:
    obj = {}

    assert _extract_refund_id("charge.refunded", obj) is None
