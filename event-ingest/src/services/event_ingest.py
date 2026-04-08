import json
import logging
import time

from core.config import settings
from core.producer_lifecycle import Producer
from marshmallow import ValidationError
from schemas import event_batch_schema, event_schema

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
        validated_batch = event_batch_schema.load(data)
    except ValidationError as err:
        return {"details": err.messages}, 400

    server_timestamp = int(time.time())
    events = validated_batch["events"]
    events_count = len(events)
    events_rejected = 0
    send_futures = []
    delivery_errors = 0

    for event in events:
        try:
            event = event_schema.load(event)
            event["user_id"] = user_id
            event["server_timestamp"] = server_timestamp

            future = kafka_producer.send(
                settings.kafka_topic,
                key=str(event["user_id"]).encode("utf-8"),
                value=json.dumps(event, default=str).encode("utf-8"),
            )
            send_futures.append(future)

            logger.debug(
                "Event enqueued for Kafka: topic=%s event_type=%s user_id=%s",
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

    # Confirm delivery of each accepted event to avoid false success responses.
    for future in send_futures:
        try:
            future.get(timeout=10)
        except Exception as err:
            logger.error("Event delivery failed: %s", err)
            delivery_errors += 1

    events_accepted = events_count - events_rejected - delivery_errors

    if delivery_errors:
        logger.warning(
            "Event batch partial failure: user_id=%s accepted=%d failed=%d validation_errors=%d",
            user_id,
            events_accepted,
            delivery_errors,
            events_rejected,
        )
        return {
            "status": "partial_failure",
            "details": "Some events failed to deliver to Kafka",
            "events_accepted": events_accepted,
            "events_rejected": events_rejected + delivery_errors,
        }, 503

    logger.info(
        "Event batch processed successfully: user_id=%s events_accepted=%d events_rejected=%d",
        user_id,
        events_accepted,
        events_rejected,
    )

    return {
        "status": "success",
        "events_accepted": events_accepted,
        "events_rejected": events_rejected,
    }, 200
