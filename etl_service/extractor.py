import os
from contextlib import closing
from datetime import datetime
from typing import Any

import psycopg
from backoff import backoff
from dotenv import load_dotenv
from logger import logger
from psycopg import sql
from psycopg.rows import dict_row
from state import State
from table_names import TableNames

load_dotenv()

POSTGRES_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB", "movies_database"),
    "user": os.getenv("POSTGRES_USER", "app"),
    "password": os.getenv("POSTGRES_PASSWORD", "123qwe"),
    "host": os.getenv("SQL_HOST", "localhost"),
    "port": int(os.getenv("SQL_PORT", "6543")),
    "options": os.getenv("SQL_OPTIONS", "-c search_path=public,content"),
}
POSTGRES_BATCH_SIZE = int(os.getenv("POSTGRES_BATCH_SIZE", "1000"))


class PostgresExtractor:
    """
    Extracts film work data from PostgreSQL database with change tracking.

    This class handles the extraction of film work records from a PostgreSQL database,
    tracking changes based on modification timestamps. It supports extracting data
    directly from the film_work table or indirectly through related genre and person tables.

    Attributes:
        connection_factory (Callable): Factory function to create database connections
        batch_size (int): Number of records to fetch per batch
        state (State): State manager for tracking last processed timestamps
        table_name (TableNames): Name of the table being monitored for changes
        last_modified (str): ISO format timestamp of last processed record
        temp_film_work_last_modified (str): Temporary timestamp for film work records
            during related table processing

    Methods:
        get_film_work_batch: Main entry point to fetch a batch of film work records

    Private Methods:
        _update_last_modified: Updates the last processed timestamp in state
        _process_record_related_film_work: Processes changes from genre/person tables
        _process_film_work: Processes changes directly from film_work table
        _execute_query: Executes SQL queries with automatic retry logic
        _get_record_id_modified_batch: Fetches modified record IDs from monitored table
        _get_film_work_for_related_ids_batch: Finds film works related to changed records
        _get_complete_film_work_data: Retrieves complete film work data with all relations

    Example:
        >>> state = State(storage)
        >>> extractor = PostgresExtractor(state, TableNames.GENRE)
        >>> batch = extractor.get_film_work_batch()
    """

    def __init__(self, state: State, table_name: TableNames) -> None:
        self.connection_factory = lambda: psycopg.connect(**POSTGRES_CONFIG)
        self.batch_size = POSTGRES_BATCH_SIZE
        self.state: State = state
        self.table_name: TableNames = table_name
        self.last_modified: str = self.state.get_state(self.table_name.value)
        self.temp_film_work_last_modified: str = "0001-01-01T00:00:00.000000+00:00"
        logger.info(
            f"Initialized PostgresExtractor for table '{self.table_name}' with last_modified = {self.last_modified}"
        )

    def get_film_work_batch(self) -> list[dict[str, Any]]:
        """
        Retrieve a batch of film work records based on the current table being processed.

        This method determines the appropriate processing strategy based on the table name
        and returns a list of film work dictionaries.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing film work data.
                Each dictionary represents a film work record with its associated attributes.

        Raises:
            ValueError: If the table_name is not one of the supported table names
                (GENRE, PERSON, or FILM_WORK).

        Note:
            - For GENRE and PERSON tables, processes records through their relationships
              to film works via _process_record_related_film_work().
            - For FILM_WORK table, processes records directly via _process_film_work().
        """
        match self.table_name:
            case TableNames.GENRE | TableNames.PERSON:
                return self._process_record_related_film_work()
            case TableNames.FILM_WORK:
                return self._process_film_work()
            case _:
                raise ValueError(f"Unsupported table name: {self.table_name}")

    @backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
    def _update_last_modified(self, timestamp: datetime) -> None:
        """
        Update the last modified timestamp for the current table.

        This method updates both the instance's last_modified attribute and persists
        the new timestamp to the state storage for the specified table.

        Args:
            timestamp (datetime): The new timestamp to set as the last modified time.

        Returns:
            None

        Side Effects:
            - Updates self.last_modified with the ISO format string of the timestamp
            - Persists the new timestamp to state storage via self.state.set_state()
            - Logs an info message about the timestamp update
        """
        new_timestamp: str = timestamp.isoformat()
        logger.info(
            f"Updating last_modified for table '{self.table_name}' from {self.last_modified} "
            f"to {new_timestamp}"
        )
        self.last_modified = new_timestamp
        self.state.set_state(self.table_name.value, new_timestamp)

    def _set_temp_film_work_last_modified(self, timestamp: datetime) -> None:
        """
        Set the temporary film work last modified timestamp.

        This method updates the temporary last modified timestamp used when processing
        film works related to changes in other tables (genre or person).

        Args:
            timestamp (datetime): The new timestamp to set as the temporary last modified time.

        Returns:
            None

        Side Effects:
            - Updates self.temp_film_work_last_modified with the ISO format string of the timestamp
        """
        self.temp_film_work_last_modified = timestamp.isoformat()

    def _reset_temp_film_work_last_modified(self) -> None:
        """
        Reset the temporary film work last modified timestamp to the default value.

        This method sets the temporary last modified timestamp back to the initial
        default value used for processing film works related to changes in other tables.

        Returns:
            None

        Side Effects:
            - Sets self.temp_film_work_last_modified to "0001-01-01T00:00:00.000000+00:00"
        """
        self.temp_film_work_last_modified = "0001-01-01T00:00:00.000000+00:00"

    def _process_record_related_film_work(self) -> list[dict[str, Any]]:
        """
        Process records from a related table and retrieve corresponding film work data.

        This method continuously processes batches of modified records from a related table
        (e.g., persons, genres) and fetches the complete film work data associated with those records.

        The method performs the following steps:
        1. Retrieves a batch of modified records based on their modification timestamp
        2. Extracts record IDs from the batch
        3. Queries for film work records related to these IDs
        4. Updates tracking timestamps for processed records
        5. Retrieves complete film work data for the found film work IDs

        Returns:
            list[dict[str, Any]]: A list of complete film work records with all related data,
                                  or an empty list if no data is available to process.

        Notes:
            - The method runs in a loop until it finds film work records to process
            - If no film work records are found for a batch, it updates the last modified
              timestamp and continues to the next batch
            - Temporary film work last modified timestamp is managed to track processing state
            - Duplicate film work IDs are removed before fetching complete data
        """

        while True:
            data_batch = self._get_record_id_modified_batch()
            if not data_batch:
                return []

            record_ids = [record["id"] for record in data_batch]
            logger.info(
                f"Processing {len(record_ids)} modified records from table '{self.table_name}'"
            )

            film_work_records = self._get_film_work_for_related_ids_batch(record_ids)
            logger.info(
                f"Found {len(film_work_records)} related film work records for modified '{self.table_name}' records"
            )

            if not film_work_records:
                self._update_last_modified(data_batch[-1]["modified"])
                self._reset_temp_film_work_last_modified()
                continue

            film_work_ids = list({record["id"] for record in film_work_records})

            self._set_temp_film_work_last_modified(film_work_records[-1]["modified"])

            return self._get_complete_film_work_data(film_work_ids)

    def _process_film_work(self) -> list[dict[str, Any]]:
        """
        Process a batch of film work records and retrieve their complete data.

        This method orchestrates the extraction of film work records by:
        1. Fetching a batch of modified film work records
        2. Updating the last modified timestamp from the batch
        3. Extracting unique film work IDs from the records
        4. Retrieving complete film work data for those IDs

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing complete film work data,
                including all related information. Returns an empty list if no records are found.

        Note:
            The method updates the internal state by storing the last modified timestamp
            from the processed batch for subsequent incremental extractions.
        """
        film_work_records = self._get_record_id_modified_batch()

        if not film_work_records:
            return []

        self._update_last_modified(film_work_records[-1]["modified"])

        film_work_ids = list({record["id"] for record in film_work_records})

        return self._get_complete_film_work_data(film_work_ids)

    @backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
    def _execute_query(self, query: sql.SQL, params: tuple) -> list[dict[str, Any]]:
        """Execute a SQL query and return results as a list of dictionaries.

        This method creates a database connection, executes the provided SQL query
        with the given parameters, and returns all results as a list of dictionaries
        where each dictionary represents a row with column names as keys.

        Args:
            query (sql.SQL): A psycopg SQL query object to be executed.
            params (tuple): A tuple of parameters to be safely interpolated into the query.

        Returns:
            list[dict[str, Any]]: A list of dictionaries where each dictionary represents
                a database row with column names as keys and corresponding values.

        Note:
            The method uses context managers to ensure proper resource cleanup.
            The connection and cursor are automatically closed after execution.
        """
        with closing(self.connection_factory()) as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, params)
                return list(cur.fetchall())

    def _get_record_id_modified_batch(self) -> list[dict[str, Any]]:
        """
        Retrieve a batch of records with their IDs and modification timestamps.

        Fetches records from the specified table that have been modified after
        the last known modification timestamp, ordered by modification time.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing 'id' and
                'modified' fields for each record in the batch.

        Notes:
            - The query filters records where modified > last_modified
            - Results are ordered by modification time in ascending order
            - The number of records returned is limited by batch_size
            - Uses parameterized queries to prevent SQL injection
        """

        query = sql.SQL("""
            SELECT id, modified
            FROM content.{table}
            WHERE modified > %s
            ORDER BY modified
            LIMIT %s;
        """).format(table=sql.Identifier(self.table_name.value))
        return self._execute_query(query, (self.last_modified, self.batch_size))

    @backoff(start_sleep_time=0.1, factor=2, border_sleep_time=10)
    def _get_film_work_for_related_ids_batch(
        self, ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Retrieve film work records associated with a batch of related entity IDs.

        This method fetches film work records that are linked to the provided entity IDs
        through a many-to-many relationship table. It only returns film works that have
        been modified after a specified timestamp.

        Args:
            ids (list[str]): A list of entity IDs (e.g., person IDs or genre IDs) to find
                associated film works for.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing film work data, where
                each dictionary has 'id' and 'modified' keys. Results are ordered by
                modification time and limited by batch_size.

        Note:
            The method constructs a dynamic SQL query based on self.table_name to join
            the appropriate relationship table (e.g., 'person_film_work' or 'genre_film_work').
            It filters results by self.temp_film_work_last_modified and limits results
            by self.batch_size.
        """

        query = sql.SQL("""
            SELECT fw.id, fw.modified
            FROM content.film_work fw
            INNER JOIN content.{table_name} rfw ON rfw.film_work_id = fw.id
            WHERE rfw.{related_column_name} = ANY(%s) AND fw.modified > %s
            ORDER BY fw.modified
            LIMIT %s;
        """).format(
            table_name=sql.Identifier(f"{self.table_name.value}_film_work"),
            related_column_name=sql.Identifier(f"{self.table_name.value}_id"),
        )
        return self._execute_query(
            query, (ids, self.temp_film_work_last_modified, self.batch_size)
        )

    def _get_complete_film_work_data(
        self, film_work_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Retrieve complete film work data including genres, directors, actors, and writers.

        This method fetches comprehensive information about film works from the database,
        including associated genres and persons (directors, actors, writers) grouped by
        their roles.

        Args:
            film_work_ids (list[str]): A list of film work UUIDs to retrieve data for.

        Returns:
            list[dict[str, Any]]: A list of dictionaries, where each dictionary contains:
                - id: Film work UUID
                - imdb_rating: IMDb rating of the film
                - title: Title of the film work
                - description: Description of the film work
                - rating: Rating of the film work
                - genres: List of genre objects with 'id' and 'name' fields
                - directors: List of person objects with 'id', 'full_name', and 'role' fields
                - actors: List of person objects with 'id', 'full_name', and 'role' fields
                - writers: List of person objects with 'id', 'full_name', and 'role' fields

        Note:
            Empty arrays are returned for genres, directors, actors, or writers if none exist
            for a given film work.
        """

        query = sql.SQL("""
            SELECT
                fw.id,
                fw.rating AS imdb_rating, 
                fw.title, 
                fw.description, 
                fw.rating, 
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object('id', g.id, 'name', g.name)
                    ) FILTER (WHERE g.id IS NOT NULL),
                    '[]'
                ) as genres,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object('id', p.id, 'full_name', p.full_name, 'role', pfw.role)
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'director'),
                    '[]'
                ) as directors,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object('id', p.id, 'full_name', p.full_name, 'role', pfw.role)
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'actor'),
                    '[]'
                ) as actors,
                COALESCE(
                    json_agg(
                        DISTINCT jsonb_build_object('id', p.id, 'full_name', p.full_name, 'role', pfw.role)
                    ) FILTER (WHERE p.id IS NOT NULL AND pfw.role = 'writer'),
                    '[]'
                ) as writers
            FROM content.film_work fw
            LEFT JOIN content.person_film_work pfw ON pfw.film_work_id = fw.id
            LEFT JOIN content.person p ON p.id = pfw.person_id
            LEFT JOIN content.genre_film_work gfw ON gfw.film_work_id = fw.id
            LEFT JOIN content.genre g ON g.id = gfw.genre_id
            WHERE fw.id = ANY(%s)
            GROUP BY fw.id, fw.title, fw.description, fw.rating
        """)
        return self._execute_query(query, (film_work_ids,))
