import json
import logging
import time

from marshmallow import ValidationError

from core.config import settings
from core.producer_lifecycle import Producer
from schemas import EventApiSchema, EventBatchSchema

logger = logging.getLogger(__name__)


def process_event_batch(
    data: object,
    user_id: str | None,
    kafka_producer: Producer,
) -> tuple[dict[str, object], int]:
    """Validate, enrich, and publish an incoming batch of user events.

    Returns a tuple of response payload and HTTP status code.
    """
    logger.info("Received event batch from user_id=%s", user_id)

    if data is None:
        return {"details": {"_schema": ["No input data provided"]}}, 400

    try:
        validated_batch = EventBatchSchema().load(data)
    except ValidationError as err:
        return {"details": err.messages}, 400

    server_timestamp = int(time.time())
    events = validated_batch["events"]
    events_count = len(events)
    events_rejected = 0

    for event in events:
        try:
            event = EventApiSchema().load(event)
            event["user_id"] = user_id
            event["server_timestamp"] = server_timestamp

            kafka_producer.send(
                settings.kafka_topic,
                key=str(event["user_id"]).encode("utf-8"),
                value=json.dumps(event, default=str).encode("utf-8"),
            ).add_errback(
                lambda exc: logger.error("Failed to send event to Kafka: %s", exc)
            )

            logger.debug(
                "Event sent to Kafka: topic=%s event_type=%s user_id=%s",
                settings.kafka_topic,
                event.get("event_type"),
                event.get("user_id"),
            )
        except ValidationError as err:
            logger.warning(
                "Validation error for event from user_id=%s: %s",
                user_id,
                err.messages,
            )
            events_rejected += 1

    events_accepted = events_count - events_rejected
    logger.info(
        "Event batch processed: user_id=%s events_accepted=%d events_rejected=%d",
        user_id,
        events_accepted,
        events_rejected,
    )

    return {
        "status": "success",
        "events_accepted": events_accepted,
        "events_rejected": events_rejected,
    }, 200
