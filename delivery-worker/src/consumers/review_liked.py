"""Consumer for notifications.events.review_liked topic.

Each message: { review_id, review_author_id, liker_user_id }
Applies per-author daily throttle via Redis before sending.
"""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
import orjson
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.core.db import async_session
from src.services import (
    auth_client,
    email,
    idempotency,
    template_renderer,
    throttle,
)

logger = logging.getLogger(__name__)

TOPIC = "notifications.events.review_liked"
DLQ_TOPIC = "notifications.delivery.dlq"
# Template name seeded in migration 0001
TEMPLATE_NAME = "review_liked"
DOMAIN_EXCEPTIONS = (KeyError, ValueError, TypeError)
RETRYABLE_EXCEPTIONS = (
    SQLAlchemyError,
    httpx.HTTPError,
    TimeoutError,
    ConnectionError,
)


async def run() -> None:
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"{settings.kafka_consumer_group}-review-liked",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=orjson.loads,
    )
    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    await consumer.start()
    await dlq_producer.start()
    logger.info("review_liked consumer started, topic=%s", TOPIC)
    try:
        async for msg in consumer:
            should_commit = await _process_message(msg.value, dlq_producer)
            if should_commit:
                await consumer.commit()
    finally:
        await consumer.stop()
        await dlq_producer.stop()


async def _process_message(payload: dict, dlq_producer: AIOKafkaProducer) -> bool:
    max_attempts = max(1, settings.consumer_max_retries)
    for attempt in range(1, max_attempts + 1):
        try:
            await _handle(payload, dlq_producer)
        except DOMAIN_EXCEPTIONS as exc:
            logger.warning("Dropping invalid review_liked payload to DLQ: %s", exc)
            await _publish_dlq(
                dlq_producer, payload, f"domain_error:{type(exc).__name__}"
            )
            return True
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt == max_attempts:
                logger.exception(
                    "Retryable review_liked error exhausted attempts=%d, sending to DLQ",
                    max_attempts,
                )
                await _publish_dlq(
                    dlq_producer,
                    payload,
                    f"retry_exhausted:{type(exc).__name__}",
                )
                return True

            delay = settings.consumer_retry_delay_seconds * attempt
            logger.warning(
                "Retryable review_liked error on attempt %d/%d, retry in %.2fs",
                attempt,
                max_attempts,
                delay,
                exc_info=True,
            )
            await asyncio.sleep(delay)
        except Exception as exc:
            logger.exception("Unexpected review_liked error, sending to DLQ")
            await _publish_dlq(
                dlq_producer, payload, f"unexpected_error:{type(exc).__name__}"
            )
            return True
        else:
            return True

    return True


async def _handle(payload: dict, dlq_producer: AIOKafkaProducer) -> None:
    review_id: str = payload.get("review_id", "")
    review_author_id: str = payload.get("review_author_id", "")
    liker_user_id: str = payload.get("liker_user_id", "")

    idempotency_key = f"review_liked:{review_id}:{liker_user_id}"

    reserved = await idempotency.reserve_key(
        campaign_id=None,
        user_id=review_author_id,
        channel="EMAIL",
        idempotency_key=idempotency_key,
    )
    if not reserved:
        logger.debug("Skipping duplicate review_liked key=%s", idempotency_key)
        return

    # Throttle: one email per author per day
    if await throttle.is_throttled(review_author_id):
        logger.info(
            "review_liked throttled for author %s (review %s)",
            review_author_id,
            review_id,
        )
        await idempotency.finalize_key(
            idempotency_key=idempotency_key,
            status="THROTTLED",
        )
        return

    # Fetch template from DB
    template = await _get_review_liked_template()
    if template is None:
        logger.error("review_liked template not found in DB, dropping message")
        await idempotency.finalize_key(
            idempotency_key=idempotency_key,
            status="FAILED",
            error="Template not found",
        )
        await _publish_dlq(dlq_producer, payload, "template_not_found")
        return

    # Fetch author's email
    user = await auth_client.get_user(review_author_id)
    if user is None:
        logger.warning(
            "User %s not found, dropping review_liked delivery", review_author_id
        )
        await idempotency.finalize_key(
            idempotency_key=idempotency_key,
            status="FAILED",
            error="User not found",
        )
        await _publish_dlq(dlq_producer, payload, "user_not_found")
        return

    to_email: str = user["email"]
    first_name: str = user.get("first_name") or ""
    last_name: str = user.get("last_name") or ""
    to_name = f"{first_name} {last_name}".strip() or to_email

    variables = {
        "first_name": first_name,
        "last_name": last_name,
        "review_id": review_id,
        "review_text_preview": f"review #{review_id}",
        "likes_count": 1,
    }
    subject, body = template_renderer.render(
        template["subject_template"], template["body_template"], variables
    )

    ok = await email.send_email(to_email, to_name, subject, body)
    sent_at: datetime | None = None
    error: str | None = None
    status = "FAILED"
    if ok:
        status = "SENT"
        sent_at = datetime.now(UTC)
        await throttle.set_throttle(review_author_id)
    else:
        error = "Brevo send_transac_email returned error"

    await idempotency.finalize_key(
        idempotency_key=idempotency_key,
        status=status,
        sent_at=sent_at,
        error=error,
    )


_cached_template: dict | None = None


async def _get_review_liked_template() -> dict | None:
    global _cached_template  # noqa: PLW0603
    if _cached_template is not None:
        return _cached_template

    async with async_session() as session:
        row = await session.execute(
            text(
                "SELECT subject_template, body_template "
                "FROM notif.templates WHERE name = :name"
            ),
            {"name": TEMPLATE_NAME},
        )
        result = row.mappings().first()
        if result:
            _cached_template = dict(result)
    return _cached_template


async def _publish_dlq(
    producer: AIOKafkaProducer,
    payload: dict,
    reason: str,
) -> None:
    message = {
        "reason": reason,
        "source_topic": TOPIC,
        "payload": payload,
    }
    key = str(payload.get("review_id", reason)).encode()
    await producer.send(
        DLQ_TOPIC,
        key=key,
        value=orjson.dumps(message),
    )
