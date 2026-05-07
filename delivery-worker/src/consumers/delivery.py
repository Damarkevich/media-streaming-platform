"""Consumer for notifications.delivery topic.

Each message represents a pre-fanned-out delivery task:
  campaign_id, user_id, template_id, template_variables, channel, idempotency_key
"""

import asyncio
import logging
import uuid

import httpx
import orjson
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.core.db import async_session
from src.services import idempotency, notification_sender

logger = logging.getLogger(__name__)

TOPIC = "notifications.delivery"
DLQ_TOPIC = "notifications.delivery.dlq"
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
        group_id=settings.kafka_consumer_group,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=orjson.loads,
    )
    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    await consumer.start()
    await dlq_producer.start()
    logger.info("delivery consumer started, topic=%s", TOPIC)
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
            logger.warning("Dropping invalid payload to DLQ: %s", exc)
            await _publish_dlq(
                dlq_producer, payload, f"domain_error:{type(exc).__name__}"
            )
            return True
        except RETRYABLE_EXCEPTIONS as exc:
            if attempt == max_attempts:
                logger.exception(
                    "Retryable error exhausted attempts=%d, sending to DLQ",
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
                "Retryable error on attempt %d/%d, retry in %.2fs",
                attempt,
                max_attempts,
                delay,
                exc_info=True,
            )
            await asyncio.sleep(delay)
        except Exception as exc:
            logger.exception("Unexpected consumer error, sending to DLQ")
            await _publish_dlq(
                dlq_producer, payload, f"unexpected_error:{type(exc).__name__}"
            )
            return True
        else:
            return True

    return True


async def _handle(payload: dict, dlq_producer: AIOKafkaProducer) -> None:
    idempotency_key: str = payload.get("idempotency_key", "")
    user_id: str = payload.get("user_id", "")
    campaign_id: str | None = payload.get("campaign_id")
    template_id: str = payload.get("template_id", "")
    template_variables: dict = payload.get("template_variables", {})

    async with async_session() as session:
        # Reserve idempotency key first (at-least-once safe pattern).
        reserved = await idempotency.reserve_key(
            campaign_id=campaign_id,
            user_id=user_id,
            channel="EMAIL",
            idempotency_key=idempotency_key,
            session=session,
        )
        if not reserved:
            logger.debug("Skipping duplicate delivery key=%s", idempotency_key)
            return

        # Fetch template from DB
        tpl_row = await session.execute(
            text(
                "SELECT subject_template, body_template FROM notif.templates WHERE id = :id"
            ),
            {"id": uuid.UUID(template_id)},
        )
        tpl = tpl_row.mappings().first()
        if tpl is None:
            logger.error("Template %s not found, dropping message", template_id)
            await idempotency.finalize_key(
                idempotency_key=idempotency_key,
                status="FAILED",
                error="Template not found",
                session=session,
            )
            await _publish_dlq(dlq_producer, payload, "template_not_found")
            return

        # Send notification (user fetch, render, email send, delivery recording)
        ok = await notification_sender.send_notification(
            session=session,
            user_id=user_id,
            template=tpl,
            variables=template_variables,
            idempotency_key=idempotency_key,
        )
        if not ok:
            await _publish_dlq(dlq_producer, payload, "send_failed")


async def _publish_dlq(
    producer: AIOKafkaProducer,
    payload: dict,
    reason: str,
) -> None:
    """Publish non-processable messages to DLQ for later inspection/replay."""
    message = {"reason": reason, "payload": payload}
    key = str(payload.get("idempotency_key", reason)).encode()
    await producer.send(
        DLQ_TOPIC,
        key=key,
        value=orjson.dumps(message),
    )
