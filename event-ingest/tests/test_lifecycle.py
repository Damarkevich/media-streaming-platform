from core import producer_lifecycle as lifecycle


class DummyProducer:
    def __init__(self) -> None:
        self.flush_calls = 0
        self.close_calls = 0

    def flush(self) -> None:
        self.flush_calls += 1

    def close(self) -> None:
        self.close_calls += 1


class FailingProducer:
    def __init__(self) -> None:
        self.close_calls = 0

    def flush(self) -> None:
        raise RuntimeError("flush failed")

    def close(self) -> None:
        self.close_calls += 1
        raise RuntimeError("close failed")


def test_register_producer_shutdown_registers_atexit_once(monkeypatch) -> None:
    registered_callbacks = []

    monkeypatch.setattr(lifecycle, "_producers_to_close", [])
    monkeypatch.setattr(lifecycle, "_shutdown_registered", False)
    monkeypatch.setattr(
        lifecycle.atexit,
        "register",
        lambda callback: registered_callbacks.append(callback),
    )

    lifecycle.register_producer_shutdown(DummyProducer())
    lifecycle.register_producer_shutdown(DummyProducer())

    assert len(registered_callbacks) == 1
    assert len(lifecycle._producers_to_close) == 2


def test_shutdown_producers_flushes_and_closes_all(monkeypatch) -> None:
    producer_1 = DummyProducer()
    producer_2 = DummyProducer()

    monkeypatch.setattr(lifecycle, "_producers_to_close", [producer_1, producer_2])

    lifecycle.shutdown_producers()

    assert producer_1.flush_calls == 1
    assert producer_1.close_calls == 1
    assert producer_2.flush_calls == 1
    assert producer_2.close_calls == 1
    assert lifecycle._producers_to_close == []


def test_shutdown_producers_swallows_producer_exceptions(monkeypatch) -> None:
    failing_producer = FailingProducer()

    monkeypatch.setattr(lifecycle, "_producers_to_close", [failing_producer])

    lifecycle.shutdown_producers()

    assert failing_producer.close_calls == 1
    assert lifecycle._producers_to_close == []


def test_create_kafka_producer_uses_explicit_api_version(monkeypatch) -> None:
    captured = {}

    def fake_kafka_producer(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(lifecycle, "KafkaProducer", fake_kafka_producer)

    lifecycle.create_kafka_producer(["kafka-0:9092"], (3, 4))

    assert captured == {
        "bootstrap_servers": ["kafka-0:9092"],
        "api_version": (3, 4),
    }
