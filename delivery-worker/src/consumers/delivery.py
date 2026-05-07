"""Consumer for notifications.delivery topic.

Each message represents a pre-fanned-out delivery task:
  campaign_id, user_id, template_id, template_variables, channel, idempotency_key
"""

import logging
import uuid
from datetime import UTC, datetime

import orjson
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from sqlalchemy import text

from src.core.config import settings
from src.core.db import async_session
from src.services import auth_client, email, idempotency, template_renderer

logger = logging.getLogger(__name__)

TOPIC = "notifications.delivery"
DLQ_TOPIC = "notifications.delivery.dlq"


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
            await _handle(msg.value, dlq_producer)
            await consumer.commit()
    finally:
        await consumer.stop()
        await dlq_producer.stop()


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

        # Fetch template
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

        # Fetch user email
        user = await auth_client.get_user(user_id)
        if user is None:
            logger.warning("User %s not found, dropping delivery", user_id)
            await idempotency.finalize_key(
                idempotency_key=idempotency_key,
                status="FAILED",
                error="User not found",
                session=session,
            )
            await _publish_dlq(dlq_producer, payload, "user_not_found")
            return

        to_email: str = user["email"]
        first_name: str = user.get("first_name") or ""
        last_name: str = user.get("last_name") or ""
        to_name = f"{first_name} {last_name}".strip() or to_email

        # Render
        variables = {
            "first_name": first_name,
            "last_name": last_name,
            **template_variables,
        }
        subject, body = template_renderer.render(
            tpl["subject_template"], tpl["body_template"], variables
        )

        # Send
        sent_at: datetime | None = None
        error: str | None = None
        status = "FAILED"
        ok = await email.send_email(to_email, to_name, subject, body)
        if ok:
            status = "SENT"
            sent_at = datetime.now(UTC)
        else:
            error = "Brevo send_transac_email returned error"

        await idempotency.finalize_key(
            idempotency_key=idempotency_key,
            status=status,
            sent_at=sent_at,
            error=error,
            session=session,
        )


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
