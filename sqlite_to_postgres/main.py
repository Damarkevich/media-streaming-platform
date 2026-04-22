import logging
import os
import sqlite3
import sys
from collections.abc import Generator
from contextlib import closing
from dataclasses import asdict, astuple
from time import time

import psycopg
from data_mappers import (
    DataMapper,
    FilmWork,
    Genre,
    GenreFilmWork,
    Person,
    PersonFilmWork,
)
from dotenv import load_dotenv
from psycopg import errors as psycopg_errors
from psycopg import sql
from psycopg.rows import dict_row

load_dotenv()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("load_data")

DONOR_DB_PATH = os.getenv("DONOR_DB_PATH", "")
RECIPIENT_DB_DSL = {
    "dbname": os.getenv("RECIPIENT_DB_NAME", ""),
    "user": os.getenv("RECIPIENT_DB_USER", ""),
    "password": os.getenv("RECIPIENT_DB_PASSWORD", ""),
    "host": os.getenv("RECIPIENT_DB_HOST", ""),
    "port": os.getenv("RECIPIENT_DB_PORT", ""),
    "options": "-c search_path=content",
}
BATCH_SIZE = 100
DATA_MAPPERS = [FilmWork, Person, Genre, GenreFilmWork, PersonFilmWork]


def validate_db_settings(dsl: dict[str, str]) -> None:
    """
    Validate that all required database connection settings are provided.

    Checks if any values in the database connection dictionary are empty or None.
    Logs an error and raises ValueError if any required settings are missing.

    Args:
        dsl: A dictionary containing database connection settings (host, user,
             password, dbname, port, etc.). All values must be non-empty strings.

    Raises:
        ValueError: If any required database settings are missing or empty.

    Example:
        >>> validate_db_settings({'host': 'localhost', 'dbname': '', 'user': 'admin'})
        # ValueError: Missing required DB settings: dbname
    """
    missing = [k for k, v in dsl.items() if not v]
    if missing:
        msg = f"Missing required DB settings: {', '.join(missing)}"
        logger.error(msg)
        raise ValueError(msg)


def extract_data(
    sqlite_cursor: sqlite3.Cursor,
    data_mapper: type[DataMapper],
) -> Generator[list[sqlite3.Row], None, None]:
    """
    Extract data from SQLite database in batches.

    Args:
        sqlite_cursor: A sqlite3 cursor object used to execute queries against the database.
        data_mapper: A DataMapper class that provides the database table name and handles data mapping.

    Yields:
        A list of sqlite3.Row objects, each containing a batch of records from the database table.
        The batch size is determined by BATCH_SIZE constant.

    Example:
        >>> cursor = connection.cursor()
        >>> for batch in extract_data(cursor, UserDataMapper):
        ...     process_batch(batch)
    """
    sqlite_cursor.execute(f"SELECT * FROM {data_mapper.db_table_name()};")
    while results := sqlite_cursor.fetchmany(BATCH_SIZE):
        yield results


def transform_data(
    sqlite_cursor: sqlite3.Cursor,
    data_mapper: type[DataMapper],
) -> Generator[list[DataMapper], None, None]:
    """
    Transform data extracted from SQLite database into mapped objects.

    Extracts batches of rows from SQLite using the provided cursor and transforms
    each row into a DataMapper object using the mapper's from_sqlite_row method.

    Args:
        sqlite_cursor: An active SQLite cursor for executing database queries.
        data_mapper: A DataMapper class used to transform raw database rows into
                     mapped data objects.

    Yields:
        A list of DataMapper instances for each batch of extracted data.
    """
    for batch in extract_data(sqlite_cursor, data_mapper):
        yield [data_mapper.from_sqlite_row(dict(row)) for row in batch]


def load_data(sqlite_cursor: sqlite3.Cursor, pg_cursor: psycopg.Cursor) -> None:
    """
    Load data from SQLite database to PostgreSQL database.

    Iterates through configured data mappers, transforms data from SQLite,
    and inserts it into corresponding PostgreSQL tables in batches.
    Skips rows with conflicting IDs using ON CONFLICT clause.

    Args:
        sqlite_cursor (sqlite3.Cursor): Cursor object for SQLite database connection.
        pg_cursor (psycopg.Cursor): Cursor object for PostgreSQL database connection.

    Returns:
        None

    Raises:
        psycopg.Error: If an error occurs during PostgreSQL operations.
        sqlite3.Error: If an error occurs during SQLite operations.
    """
    for data_mapper in DATA_MAPPERS:
        logger.info(f"Loading data for table: {data_mapper.db_table_name()}")
        for batch in transform_data(sqlite_cursor, data_mapper):
            fields_to_insert: str = data_mapper.fields_to_insert()
            s_string: str = data_mapper.s_string()
            query = sql.SQL(
                "INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT (id) DO NOTHING"
            ).format(
                sql.Identifier(data_mapper.recipient_db_schema_name()),
                sql.Identifier(data_mapper.db_table_name()),
                sql.SQL(fields_to_insert),
                sql.SQL(s_string),
            )
            batch_as_tuples = [astuple(student) for student in batch]
            try:
                pg_cursor.executemany(query, batch_as_tuples)
            except psycopg_errors.Error:
                logger.exception(
                    f"Failed inserting batch into {data_mapper.recipient_db_schema_name()}."
                    f"{data_mapper.db_table_name()}"
                )
                raise


def compare_batches(
    original_batch: list[DataMapper],
    transferred_batch: list[DataMapper],
    fields_not_to_compare: tuple[str, ...],
) -> None:
    """
    Compares two batches of data to ensure that records with matching IDs are identical,
    excluding specified fields.

    Args:
        original_batch (Iterable): The original batch of data, where each item is a dataclass instance.
        transferred_batch (Iterable): The transferred batch of data, where each item is a dataclass instance.
        fields_not_to_compare (Iterable[str]): List of field names to exclude from comparison.

    Raises:
        AssertionError: If a record with a matching ID is not found in the transferred batch,
                        or if the compared records (excluding specified fields) do not match.
    """
    original_dicts = [asdict(instance) for instance in original_batch]
    transferred_dicts = [asdict(instance) for instance in transferred_batch]

    for original_dict in original_dicts:
        transferred_dict = next(
            (td for td in transferred_dicts if td["id"] == original_dict["id"]),
            None,
        )
        assert transferred_dict is not None, (
            f"Record with id {original_dict['id']} not found in transferred data"
        )

        for field in fields_not_to_compare:
            original_dict.pop(field, None)
            transferred_dict.pop(field, None)

        assert original_dict == transferred_dict, (
            f"Data mismatch for id {original_dict} vs {transferred_dict}"
        )


def test_transfer(sqlite_cursor: sqlite3.Cursor, pg_cursor: psycopg.Cursor) -> None:
    """
    Test the data transfer from SQLite to PostgreSQL databases.

    This function validates that data has been correctly transferred from SQLite to PostgreSQL
    by comparing batches of records from both databases. It iterates through all configured
    data mappers, fetches data in batches from SQLite, verifies the corresponding records
    exist in PostgreSQL, and compares their contents.

    Args:
        sqlite_cursor (sqlite3.Cursor): Cursor object for executing SQLite queries.
        pg_cursor (psycopg.Cursor): Cursor object for executing PostgreSQL queries.

    Raises:
        AssertionError: If the number of records transferred does not match the original,
                        or if record contents do not match (excluding timestamp fields).

    Logs:
        - Info: Transfer test start, per-table testing progress, and overall completion.

    Notes:
        - Processes data in batches defined by BATCH_SIZE for memory efficiency.
        - Excludes 'created', 'modified', and 'creation_date' fields from comparison.
        - Uses data_mapper instances to transform SQLite rows to objects for comparison.
    """
    logger.info("Starting data transfer test...")
    for data_mapper in DATA_MAPPERS:
        logger.info(f"Testing data for table: {data_mapper.db_table_name()}")
        sqlite_cursor.execute(f"SELECT * FROM {data_mapper.db_table_name()};")

        while batch := sqlite_cursor.fetchmany(BATCH_SIZE):
            original_batch = [data_mapper.from_sqlite_row(dict(row)) for row in batch]
            ids = [instance.id for instance in original_batch]
            query = sql.SQL("SELECT * FROM {}.{} WHERE id = ANY(%s);").format(
                sql.Identifier(data_mapper.recipient_db_schema_name()),
                sql.Identifier(data_mapper.db_table_name()),
            )
            pg_cursor.execute(query, [ids])
            transferred_batch = [
                data_mapper.from_sqlite_row(dict(student))
                for student in pg_cursor.fetchall()
            ]
            # Compare lengths of batches
            assert len(original_batch) == len(transferred_batch)

            # Compare contents of batches
            fields_not_to_compare = ("created", "modified", "creation_date")
            compare_batches(original_batch, transferred_batch, fields_not_to_compare)


if __name__ == "__main__":
    logger.info("Starting data transfer from SQLite to PostgreSQL...")
    start = time()
    try:
        validate_db_settings(RECIPIENT_DB_DSL)

        with (
            closing(sqlite3.connect(DONOR_DB_PATH)) as sqlite_conn,
            closing(psycopg.connect(**RECIPIENT_DB_DSL)) as pg_conn,
        ):
            sqlite_conn.row_factory = sqlite3.Row

            with (
                closing(sqlite_conn.cursor()) as sqlite_cur,
                closing(pg_conn.cursor(row_factory=dict_row)) as pg_cur,
            ):
                loading_start = time()
                try:
                    load_data(sqlite_cur, pg_cur)
                    pg_conn.commit()
                    logger.info(
                        f"Loading data finished in {time() - loading_start:.2f} seconds"
                    )
                except Exception:
                    logger.exception("Error during load_data, rolling back")
                    try:
                        pg_conn.rollback()
                    except Exception:
                        logger.exception("Rollback failed")
                    raise

                testing_start = time()
                try:
                    test_transfer(sqlite_cur, pg_cur)
                    logger.info(
                        f"Testing transfer finished in {time() - testing_start:.2f} seconds"
                    )
                except Exception:
                    logger.exception("Error during test_transfer")
                    raise

        logger.info(f"Data transfer completed in {time() - start:.2f} seconds")

    except (sqlite3.Error, psycopg_errors.Error):
        logger.exception("Database error")
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error")
        sys.exit(1)
