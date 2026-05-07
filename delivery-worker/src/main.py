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
from src.services.auth_client import close_http_client
from src.services.email import close_brevo_client
from src.services.throttle import close_redis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("delivery-worker starting up")
    try:
        await asyncio.gather(
            run_delivery(),
            run_review_liked(),
        )
    finally:
        results = await asyncio.gather(
            close_http_client(),
            close_redis(),
            close_brevo_client(),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("Client shutdown error: %s", result)


if __name__ == "__main__":
    asyncio.run(main())
