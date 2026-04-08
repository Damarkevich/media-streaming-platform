import atexit
from typing import Protocol

from kafka import KafkaProducer


class ProducerFuture(Protocol):
    """Minimal protocol for async producer send result."""

    def add_errback(self, callback: object) -> object: ...

    def get(self, timeout: float | None = None) -> object: ...


class Producer(Protocol):
    """Kafka-producer-like interface used by the service and tests."""

    def send(self, *args: object, **kwargs: object) -> ProducerFuture: ...

    def flush(self, timeout: float | None = None) -> None: ...

    def close(self) -> None: ...


_producers_to_close: list[Producer] = []
_shutdown_registered = False


def shutdown_producers() -> None:
    """Flush and close all registered producers on process shutdown."""
    while _producers_to_close:
        producer = _producers_to_close.pop()
        try:
            producer.flush()
        except Exception as err:
            # atexit can run after logging streams are already closed
            _ = err
        finally:
            try:
                producer.close()
            except Exception as err:
                _ = err


def register_producer_shutdown(producer: Producer) -> None:
    """Register producer for atexit cleanup, installing hook once."""
    global _shutdown_registered

    _producers_to_close.append(producer)

    if not _shutdown_registered:
        atexit.register(shutdown_producers)
        _shutdown_registered = True


def create_kafka_producer(
    bootstrap_servers: list[str],
    api_version: tuple[int, int],
) -> KafkaProducer:
    """Create a Kafka producer with configured bootstrap servers."""
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        api_version=api_version,
    )
