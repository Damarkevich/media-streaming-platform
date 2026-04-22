import logging
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import psycopg
from backoff import backoff
from config.settings import BATCH_SIZE, DEFAULT_TIMESTAMP, POSTGRES_CONFIG
from psycopg import sql
from psycopg.rows import dict_row

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DataStorage:
    movies: list[dict[str, Any]]
    genres: list[dict[str, Any]]
    persons: list[dict[str, Any]]
    new_last_modified: str = DEFAULT_TIMESTAMP

    def is_empty(self) -> bool:
        return not (self.movies or self.genres or self.persons)


class PostgresExtractor:
    def __init__(
        self,
        last_modified: str,
        table_name: Literal["film_work", "genre", "person"],
    ) -> None:
        self.connection_factory = lambda: psycopg.connect(**POSTGRES_CONFIG)
        self.batch_size = BATCH_SIZE
        self.table_name: Literal["film_work", "genre", "person"] = table_name
        self.last_modified: str = last_modified
        self.new_last_modified: str = last_modified
        self.film_work_data: list[dict[str, Any]] = []
        self.genres_data: list[dict[str, Any]] = []
        self.persons_data: list[dict[str, Any]] = []
        logger.info(
            f"Initialized PostgresExtractor for table '{self.table_name}' with last_modified = {self.last_modified}"
        )

    def get_data_batch(self) -> DataStorage:
        match self.table_name:
            case "genre":
                self._process_genre_data()
            case "person":
                self._process_person_data()
            case "film_work":
                self._process_film_work_data()
            case _:
                msg = f"Unsupported table name: {self.table_name}"
                raise ValueError(msg)
        return DataStorage(
            movies=self.film_work_data,
            genres=self.genres_data,
            persons=self.persons_data,
            new_last_modified=self.new_last_modified,
        )

    def _process_film_work_data(self) -> None:
        film_work_records = self._get_record_id_modified_batch()
        if not film_work_records:
            return

        film_work_ids = list({record["id"] for record in film_work_records})
        self.film_work_data = self._get_complete_film_work_data(film_work_ids)

        new_last_modified: datetime = max(
            record["modified"] for record in film_work_records
        )
        self.new_last_modified = new_last_modified.isoformat()

    def _process_genre_data(self) -> None:
        genres_records = self._get_record_id_modified_batch()
        if not genres_records:
            return

        genre_ids = [record["id"] for record in genres_records]
        self.genres_data = self._get_complete_genre_data(genre_ids)

        film_work_records = self._get_film_work_for_related_ids(genre_ids)
        if not film_work_records:
            return

        film_work_ids = list({record["id"] for record in film_work_records})
        self.film_work_data = self._get_complete_film_work_data(film_work_ids)

        new_last_modified: datetime = max(
            record["modified"] for record in genres_records
        )
        self.new_last_modified = new_last_modified.isoformat()

    def _process_person_data(self) -> None:
        persons_records = self._get_record_id_modified_batch()
        if not persons_records:
            return

        person_ids = [record["id"] for record in persons_records]
        self.persons_data = self._get_complete_person_data(person_ids)

        film_work_records = self._get_film_work_for_related_ids(person_ids)
        if not film_work_records:
            return

        film_work_ids = list({record["id"] for record in film_work_records})
        self.film_work_data = self._get_complete_film_work_data(film_work_ids)
        new_last_modified: datetime = max(
            record["modified"] for record in persons_records
        )
        self.new_last_modified = new_last_modified.isoformat()

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
        with (
            closing(self.connection_factory()) as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
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
        """).format(table=sql.Identifier(self.table_name))
        return self._execute_query(query, (self.last_modified, self.batch_size))

    def _get_film_work_for_related_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        query = sql.SQL("""
            SELECT fw.id
            FROM content.film_work fw
            INNER JOIN content.{table_name} rfw ON rfw.film_work_id = fw.id
            WHERE rfw.{related_column_name} = ANY(%s)
            ORDER BY fw.id;
        """).format(
            table_name=sql.Identifier(f"{self.table_name}_film_work"),
            related_column_name=sql.Identifier(f"{self.table_name}_id"),
        )
        return self._execute_query(query, (ids,))

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

    def _get_complete_genre_data(self, genre_ids: list[str]) -> list[dict[str, Any]]:
        query = sql.SQL("""
            SELECT
                g.id,
                g.name
            FROM content.genre g
            WHERE g.id = ANY(%s)
        """)
        return self._execute_query(query, (genre_ids,))

    def _get_complete_person_data(self, person_ids: list[str]) -> list[dict[str, Any]]:
        query = sql.SQL("""
            SELECT
                p.id,
                p.full_name,
                COALESCE(
                    (
                        SELECT json_agg(json_build_object('id', fw_inner.id, 'roles', fw_inner.roles))
                        FROM (
                            SELECT fw.id, array_agg(DISTINCT pfw_inner.role) AS roles
                            FROM content.person_film_work pfw_inner
                            JOIN content.film_work fw ON fw.id = pfw_inner.film_work_id
                            WHERE pfw_inner.person_id = p.id
                            GROUP BY fw.id
                        ) fw_inner
                    ),
                    '[]'
                ) AS films
            FROM content.person p
            WHERE p.id = ANY(%s)
        """)
        return self._execute_query(query, (person_ids,))
