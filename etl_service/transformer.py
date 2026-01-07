from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PersonLoadData(BaseModel):
    """
    Data model for person information to be loaded into the database.

    Attributes:
        id (UUID): Unique identifier for the person.
        name (str): Full name of the person.
    """

    id: UUID
    name: str


class FilmWorkLoadData(BaseModel):
    """
    Data model for film work information used in ETL loading process.

    This model represents a complete film work entry with all associated metadata,
    including ratings, genres, personnel information, and relationships.

    Attributes:
        id (UUID): Unique identifier for the film work.
        imdb_rating (float | None): IMDb rating score for the film, can be None if not rated.
        genres (list[str]): List of genre names associated with the film.
        title (str): Title of the film work.
        description (str | None): Detailed description of the film, can be None if not available.
        directors_names (list[str]): List of director names as strings.
        actors_names (list[str]): List of actor names as strings.
        writers_names (list[str]): List of writer names as strings.
        directors (list[PersonLoadData]): List of director person objects with detailed information.
        actors (list[PersonLoadData]): List of actor person objects with detailed information.
        writers (list[PersonLoadData]): List of writer person objects with detailed information.
    """

    id: UUID
    imdb_rating: float | None
    genres: list[str]
    title: str
    description: str | None
    directors_names: list[str]
    actors_names: list[str]
    writers_names: list[str]
    directors: list[PersonLoadData]
    actors: list[PersonLoadData]
    writers: list[PersonLoadData]


def transform_data(raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Transform raw film work data into a standardized format for loading.

    This function takes a list of raw film work records from the database and transforms
    them into a structured format using the FilmWorkLoadData model. Each record is
    converted to include film metadata, associated genres, and detailed information
    about directors, actors, and writers.

    Args:
        raw_data (list[dict[str, Any]]): A list of dictionaries containing raw film work data.
            Each dictionary should have the following keys:
            - id: Unique identifier for the film work
            - imdb_rating: IMDb rating of the film
            - genres: List of genre dictionaries with 'name' key
            - title: Title of the film
            - description: Description of the film
            - directors: List of director dictionaries with 'id' and 'full_name' keys
            - actors: List of actor dictionaries with 'id' and 'full_name' keys
            - writers: List of writer dictionaries with 'id' and 'full_name' keys

    Returns:
        list[dict[str, Any]]: A list of transformed film work dictionaries ready for loading.
            Each dictionary contains structured film data with flattened person names
            and detailed person objects for directors, actors, and writers.

    Example:
        >>> raw = [{"id": "123", "title": "Movie", "genres": [{"name": "Drama"}], ...}]
        >>> result = transform_data(raw)
        >>> result[0]["title"]
        'Movie'
    """
    return [
        FilmWorkLoadData(
            id=record["id"],
            imdb_rating=record["imdb_rating"],
            genres=[genre["name"] for genre in record["genres"]],
            title=record["title"],
            description=record["description"],
            directors_names=[director["full_name"] for director in record["directors"]],
            actors_names=[actor["full_name"] for actor in record["actors"]],
            writers_names=[writer["full_name"] for writer in record["writers"]],
            directors=[
                PersonLoadData(id=director["id"], name=director["full_name"])
                for director in record["directors"]
            ],
            actors=[
                PersonLoadData(id=actor["id"], name=actor["full_name"])
                for actor in record["actors"]
            ],
            writers=[
                PersonLoadData(id=writer["id"], name=writer["full_name"])
                for writer in record["writers"]
            ],
        ).model_dump()
        for record in raw_data
    ]
