import json
import logging
from typing import Any

from kafka import KafkaConsumer

from config.settings import settings

logger = logging.getLogger(settings.log_name)


class KafkaExtractor:
    """Read events from Kafka in batches and manage consumer offsets."""

    def __init__(self) -> None:
        """Create a Kafka consumer configured for manual offset commits."""
        self.consumer = KafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            group_id=settings.kafka_group_id,
            api_version=settings.kafka_api_version,
            enable_auto_commit=False,
            value_deserializer=self._deserializer,
        )

    def _deserializer(self, message: bytes) -> dict[str, Any]:
        """Deserialize a Kafka message payload from JSON bytes."""
        try:
            return json.loads(message.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to decode message: %s", e)
            return {}

    def get_batch(self) -> list[dict[str, Any]]:
        """Poll Kafka and return a flattened batch of event dictionaries."""
        polled = self.consumer.poll(
            max_records=settings.kafka_max_batch_size,
            timeout_ms=settings.kafka_poll_timeout_ms,
        )
        if not polled:
            return []

        events: list[dict[str, Any]] = []

        for records in polled.values():
            events.extend(message.value for message in records)

        return events

    def commit(self) -> None:
        """Commit consumed Kafka offsets after successful processing."""
        self.consumer.commit()

    def close(self) -> None:
        """Close the Kafka consumer connection."""
        self.consumer.close()
