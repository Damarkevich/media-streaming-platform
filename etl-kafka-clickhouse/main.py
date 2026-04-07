import logging
import time
from typing import Any

from config.logger import configure_logging
from config.settings import settings
from extractor import KafkaExtractor
from loader import ClickHouseLoader
from transformer import Transformer

logger = logging.getLogger(settings.log_name)


def run() -> None:
    """Run the Kafka -> ClickHouse ETL loop until interrupted."""
    configure_logging()
    extractor: KafkaExtractor | None = None
    transformer = Transformer()
    loader: ClickHouseLoader | None = None

    try:
        extractor = KafkaExtractor()
        loader = ClickHouseLoader()

        logger.info("Starting Kafka -> ClickHouse ETL loop.")

        while True:
            transformed_batch: list[dict[str, Any]] = []
            extracted_count: int = 0
            batch_started_at: float = time.monotonic()

            while True:
                new_events: list[dict[str, Any]] = extractor.get_batch()
                if new_events:
                    extracted_count += len(new_events)
                    transformed_batch.extend(transformer.transform(new_events))

                reached_size: bool = (
                    len(transformed_batch) >= settings.clickhouse_min_batch_size
                )
                reached_wait_timeout: bool = (
                    time.monotonic() - batch_started_at
                    >= settings.etl_batch_max_wait_seconds
                )

                if reached_size or reached_wait_timeout:
                    break

                if not new_events:
                    time.sleep(settings.etl_idle_sleep_seconds)

            if extracted_count == 0:
                continue

            logger.info(
                "Extracted %r raw events and prepared %r transformed events.",
                extracted_count,
                len(transformed_batch),
            )

            if not transformed_batch:
                logger.warning("All extracted events were invalid and skipped.")
                extractor.commit()
                continue

            loader.load_with_retry(transformed_batch)
            extractor.commit()

            logger.info("Loaded %r events into ClickHouse.", len(transformed_batch))
    finally:
        if extractor is not None:
            extractor.close()
        if loader is not None:
            loader.close()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        logger.info("ETL service interrupted and stopped.")
