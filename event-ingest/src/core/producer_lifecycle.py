import atexit
import logging
from typing import Protocol

from kafka import KafkaProducer

logger = logging.getLogger(__name__)


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
            try:
                logger.error("Error flushing producer: %s", err, exc_info=True)
            except Exception:
                pass
        finally:
            try:
                producer.close()
            except Exception as err:
                try:
                    logger.error("Error closing producer: %s", err, exc_info=True)
                except Exception:
                    pass


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
