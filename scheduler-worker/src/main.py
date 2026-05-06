"""Scheduler-worker entry point.

Reads cron expression from notif.jobs (DB), registers APScheduler job,
runs until interrupted.
"""

import asyncio
import logging
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from src.core.config import settings
from src.core.db import async_session
from src.jobs.weekly_digest import run_weekly_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _load_cron() -> str:
    """Read cron_expression from notif.jobs; fallback to settings default."""
    try:
        async with async_session() as session:
            row = await session.execute(
                text(
                    "SELECT cron_expression FROM notif.jobs WHERE name = 'weekly_digest' LIMIT 1"
                )
            )
            result = row.first()
            if result:
                return str(result[0])
    except Exception:
        logger.warning("Could not load cron from DB, using default", exc_info=True)

    return settings.weekly_digest_cron


async def main() -> None:
    cron = await _load_cron()
    logger.info("scheduler-worker starting — weekly_digest cron: %s", cron)

    # Parse "min hour dom month dow" into CronTrigger kwargs
    parts = cron.split()
    if len(parts) != 5:
        logger.warning(
            "Invalid cron from DB: %s. Falling back to default: %s",
            cron,
            settings.weekly_digest_cron,
        )
        parts = settings.weekly_digest_cron.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone="UTC",
    )

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_weekly_digest,
        trigger=trigger,
        id="weekly_digest",
        name="Weekly top-10 digest",
        misfire_grace_time=3600,
        coalesce=True,
    )
    scheduler.start()
    logger.info(
        "scheduler started, next run: %s",
        scheduler.get_job("weekly_digest").next_run_time,
    )

    try:
        # Keep the event loop alive
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("scheduler-worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
