"""Fire-and-forget Kafka producer for UGC events.

Uses kafka-python's KafkaProducer which sends in a background thread —
calling producer.send() is non-blocking and safe from async code.
The producer is lazily initialised on first use and reused thereafter.
"""

import json
import logging
from typing import Any

from kafka import KafkaProducer  # type: ignore[import-untyped]

from src.core.config import settings

logger = logging.getLogger(__name__)

_producer = None


def _get_producer():  # type: ignore[return]
    global _producer  # noqa: PLW0603
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode(),
            key_serializer=lambda k: k.encode() if isinstance(k, str) else k,
            acks=1,
            retries=3,
        )
    return _producer


def publish(topic: str, key: str, payload: dict[str, Any]) -> None:
    """Publish *payload* to *topic* with *key*. Errors are logged and swallowed."""
    try:
        _get_producer().send(topic, key=key, value=payload)
    except Exception:
        logger.exception("Failed to publish Kafka event to %s", topic)
