"""Delivery-worker entry point.

Runs two aiokafka consumers concurrently:
  1. notifications.delivery       — campaign fanout messages
  2. notifications.events.review_liked — throttled UGC events
"""

import asyncio
import logging
import sys

from src.consumers.delivery import run as run_delivery
from src.consumers.review_liked import run as run_review_liked

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("delivery-worker starting up")
    await asyncio.gather(
        run_delivery(),
        run_review_liked(),
    )


if __name__ == "__main__":
    asyncio.run(main())
