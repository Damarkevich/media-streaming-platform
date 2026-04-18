import logging
import random
import time

from config.etl_mappings import MAPPINGS, Mapping
from config.logger import configure_logging
from config.structured_logger import set_batch_id
from es_setup import es_setup
from extractor import DataStorage, PostgresExtractor
from loader import ESLoadder
from state import State
from state_setup import state_setup
from transformer import Transformer

logger = logging.getLogger(__name__)


def get_jitter() -> float:
    """
    Generate a random jitter value for retry delays.

    Returns:
        A random float between 0 and 1 seconds to add variability to retry attempts.
    """
    return random.uniform(0, 1)


def process_related_data(state: State, mapping: Mapping) -> None:
    logger.info(f"Starting ETL cycle for {mapping.postgres_table}-related data...")

    last_modified = state.get_state(mapping.postgres_table)

    extractor = PostgresExtractor(
        last_modified=last_modified, table_name=mapping.postgres_table
    )

    while True:
        data: DataStorage = extractor.get_data_batch()

        if data.is_empty():
            logger.info(f"No data to process for {mapping.postgres_table}.")
            return

        transformer = Transformer(data=data)
        data: DataStorage = transformer.transform()

        logger.info("Transformed data ready for Elasticsearch.")

        loader = ESLoadder(data=data)
        loader.load()

        # Update state with the latest modification timestamp
        new_last_modified = data.new_last_modified
        state.set_state(mapping.postgres_table, new_last_modified)

        logger.info(f"ETL cycle for {mapping.postgres_table}-related data completed.")

        # Small sleep to avoid overwhelming the system
        time.sleep(1 + get_jitter())
        return


if __name__ == "__main__":
    # Configure logging
    configure_logging()

    # Set initial batch_id for this ETL process run
    set_batch_id()

    logger.info("Starting ETL pipeline...")

    # Initial Elasticsearch setup
    new_index_created: bool = es_setup()

    # Initialize state storage
    state: State = state_setup(recreate_state=new_index_created)

    # Main ETL loop
    try:
        while True:
            logger.info("Starting full ETL cycle...")
            for mapping in MAPPINGS:
                try:
                    process_related_data(state, mapping)
                    time.sleep(1 + get_jitter())
                except Exception:
                    logger.exception(
                        f"Unhandled error while executing ETL for table '{mapping.postgres_table}' "
                        f"in ETL cycle; skipping to next step.",
                    )

            logger.info("ETL full cycle completed. Restarting...")
    except KeyboardInterrupt:
        logger.info("ETL pipeline interrupted by user. Shutting down gracefully.")
