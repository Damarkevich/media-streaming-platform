import logging
import random
import time

from config.etl_mappings import MAPPINGS, Mapping
from config.logger import configure_logging
from es_setup import es_setup
from extractor import PostgresExtractor
from loader import send_to_elasticsearch
from state import State
from state_setup import state_setup
from transformer import transform_data

logger = logging.getLogger(__name__)


def get_jitter() -> float:
    """
    Generate a random jitter value for retry delays.

    Returns:
        A random float between 0 and 0.1 seconds to add variability to retry attempts.
    """
    return random.uniform(0, 0.1)


def process_related_data(state: State, mapping: Mapping) -> None:
    """
    Process and synchronize data from a specific table to Elasticsearch.

    This function performs an ETL (Extract, Transform, Load) cycle for data related to
    a specific table. It continuously extracts batches of film work data that has been
    modified, transforms it into the appropriate format, and loads it into Elasticsearch.

    Args:
        state (State): The state object that tracks the progress of the ETL process,
            including timestamps and processed records.
        table_name (TableNames): The name of the table to process (e.g., 'person',
            'genre', 'film_work') that contains related data to synchronize.

    Returns:
        None: The function exits when there are no more records to process.

    Note:
        - The function runs in a loop until no new data is available
        - A small sleep with jitter is applied between iterations to prevent system overload
        - Progress is logged at each stage of the ETL process
        - State is automatically updated by the PostgresExtractor to track progress
    """
    logger.info(f"Starting ETL cycle for {mapping.postgres_table}-related data...")

    extractor = PostgresExtractor(state=state, table_name=mapping.postgres_table)

    while True:
        raw_data = extractor.get_film_work_batch()

        # If no new data, exit the function
        if not raw_data:
            logger.info(
                f"No new {mapping.postgres_table} records to process. Exiting ETL cycle."
            )
            return

        transformed_data = transform_data(raw_data)
        logger.info(
            f"Transformed data ready for Elasticsearch. Records count: {len(transformed_data)}"
        )
        send_to_elasticsearch("movies", transformed_data)

        logger.info(f"ETL cycle for {'movies'}-related data completed.")

        # Small sleep to avoid overwhelming the system
        time.sleep(0.1 + get_jitter())


if __name__ == "__main__":
    # Configure logging
    configure_logging()

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
