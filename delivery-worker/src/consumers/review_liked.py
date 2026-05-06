"""Consumer for notifications.events.review_liked topic.

Each message: { review_id, review_author_id, liker_user_id }
Applies per-author daily throttle via Redis before sending.
"""

import logging
from datetime import UTC, datetime

import orjson
from aiokafka import AIOKafkaConsumer
from sqlalchemy import text

from src.core.config import settings
from src.core.db import async_session
from src.services import (
    auth_client,
    delivery_record,
    email,
    template_renderer,
    throttle,
)

logger = logging.getLogger(__name__)

TOPIC = "notifications.events.review_liked"
# Template name seeded in migration 0001
TEMPLATE_NAME = "review_liked"


async def run() -> None:
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=f"{settings.kafka_consumer_group}-review-liked",
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=orjson.loads,
    )
    await consumer.start()
    logger.info("review_liked consumer started, topic=%s", TOPIC)
    try:
        async for msg in consumer:
            await _handle(msg.value)
            await consumer.commit()
    finally:
        await consumer.stop()


async def _handle(payload: dict) -> None:
    review_id: str = payload.get("review_id", "")
    review_author_id: str = payload.get("review_author_id", "")
    liker_user_id: str = payload.get("liker_user_id", "")

    idempotency_key = f"review_liked:{review_id}:{liker_user_id}"

    # Throttle: one email per author per day
    if await throttle.is_throttled(review_author_id):
        logger.info(
            "review_liked throttled for author %s (review %s)",
            review_author_id,
            review_id,
        )
        async with async_session() as session:
            await delivery_record.record_delivery(
                session,
                campaign_id=None,
                user_id=review_author_id,
                channel="EMAIL",
                idempotency_key=idempotency_key,
                status="THROTTLED",
            )
        return

    # Fetch template from DB
    template = await _get_review_liked_template()
    if template is None:
        logger.error("review_liked template not found in DB, dropping message")
        return

    # Fetch author's email
    user = await auth_client.get_user(review_author_id)
    if user is None:
        logger.warning(
            "User %s not found, dropping review_liked delivery", review_author_id
        )
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

    async with async_session() as session:
        await delivery_record.record_delivery(
            session,
            campaign_id=None,
            user_id=review_author_id,
            channel="EMAIL",
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
