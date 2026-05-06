"""Weekly digest job.

Reads the cron expression and template_id from notif.jobs (seeded in migration 0001),
fetches top-N films from async-api, fetches all user IDs from auth,
then publishes one delivery message per user to notifications.delivery.
"""

import json
import logging
import uuid
from datetime import UTC, datetime

from aiokafka import AIOKafkaProducer
from sqlalchemy import text

from src.core.config import settings
from src.core.db import async_session
from src.services.api_clients import get_all_user_ids, get_top_films

logger = logging.getLogger(__name__)

DELIVERY_TOPIC = "notifications.delivery"
JOB_NAME = "weekly_digest"


async def run_weekly_digest() -> None:
    """Entry point called by APScheduler. Fully async."""
    logger.info("weekly_digest job started at %s", datetime.now(UTC).isoformat())
    try:
        await _run()
    except Exception:
        logger.exception("weekly_digest job failed")


async def _run() -> None:
    # 1. Load template_id from DB (from notif.jobs row seeded in migration)
    template_id = await _get_template_id()
    if template_id is None:
        logger.error("weekly_digest: template_id not found in notif.jobs, aborting")
        return

    # 2. Fetch top-10 films
    films = await get_top_films(settings.weekly_digest_top_n)
    if not films:
        logger.warning("weekly_digest: no films returned from async_api, aborting")
        return

    # 3. Fetch all user IDs
    user_ids = await get_all_user_ids()
    if not user_ids:
        logger.warning("weekly_digest: no users found, aborting")
        return

    logger.info(
        "weekly_digest: publishing to %d users, top %d films",
        len(user_ids),
        len(films),
    )

    # 4. Publish one delivery message per user
    films_html = "".join(
        f"<li>{f.get('title', 'Unknown')} — ⭐ {f.get('imdb_rating', '')}</li>"
        for f in films
    )
    template_variables = {"films_list": f"<ol>{films_html}</ol>"}
    week_tag = datetime.now(UTC).strftime("%Y-W%W")
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    await producer.start()
    try:
        for user_id in user_ids:
            idempotency_key = f"weekly_digest:{week_tag}:user:{user_id}"
            message = {
                "campaign_id": None,
                "user_id": user_id,
                "template_id": str(template_id),
                "template_variables": template_variables,
                "channel": "EMAIL",
                "idempotency_key": idempotency_key,
            }
            await producer.send(
                DELIVERY_TOPIC,
                key=idempotency_key.encode(),
                value=json.dumps(message).encode(),
            )
    finally:
        await producer.stop()

    # 5. Update last_run_at in notif.jobs
    await _update_last_run()
    logger.info("weekly_digest: done")


async def _get_template_id() -> uuid.UUID | None:
    async with async_session() as session:
        row = await session.execute(
            text("SELECT template_id FROM notif.jobs WHERE name = :name LIMIT 1"),
            {"name": JOB_NAME},
        )
        result = row.first()
        return uuid.UUID(str(result[0])) if result else None


async def _update_last_run() -> None:
    async with async_session() as session:
        await session.execute(
            text("UPDATE notif.jobs SET last_run_at = :now WHERE name = :name"),
            {"now": datetime.now(UTC), "name": JOB_NAME},
        )
        await session.commit()
