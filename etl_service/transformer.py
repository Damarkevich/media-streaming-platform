from typing import Any
from uuid import UUID

from pydantic import BaseModel

from extractor import DataStorage


class MovieForPersonLoadData(BaseModel):
    id: UUID
    roles: list[str]


class PersonLoadData(BaseModel):
    id: UUID
    full_name: str
    films: list[MovieForPersonLoadData]


class PersonForMoviesLoadData(BaseModel):
    id: UUID
    full_name: str


class GenreLoadData(BaseModel):
    id: UUID
    name: str


class MovieLoadData(BaseModel):
    id: UUID
    imdb_rating: float | None
    title: str
    description: str
    genres_names: list[str]
    directors_names: list[str]
    actors_names: list[str]
    writers_names: list[str]
    genres: list[GenreLoadData]
    directors: list[PersonForMoviesLoadData]
    actors: list[PersonForMoviesLoadData]
    writers: list[PersonForMoviesLoadData]


class Transformer:
    def __init__(self, data: DataStorage) -> None:
        self.data: DataStorage = data

    def transform(self) -> DataStorage:
        self.data.movies = self._transform_movies_data()
        self.data.persons = self._transform_persons_data()
        self.data.genres = self._transform_genres_data()
        return self.data

    def _transform_movies_data(self) -> list[dict[str, Any]]:
        return [
            MovieLoadData(
                id=movie["id"],
                imdb_rating=movie["imdb_rating"],
                title=movie["title"],
                description=movie["description"] or "",
                genres_names=[genre["name"] for genre in movie["genres"]],
                directors_names=[
                    director["full_name"] for director in movie["directors"]
                ],
                actors_names=[actor["full_name"] for actor in movie["actors"]],
                writers_names=[writer["full_name"] for writer in movie["writers"]],
                genres=[
                    GenreLoadData(id=genre["id"], name=genre["name"])
                    for genre in movie["genres"]
                ],
                directors=[
                    PersonForMoviesLoadData(
                        id=director["id"], full_name=director["full_name"]
                    )
                    for director in movie["directors"]
                ],
                actors=[
                    PersonForMoviesLoadData(
                        id=actor["id"], full_name=actor["full_name"]
                    )
                    for actor in movie["actors"]
                ],
                writers=[
                    PersonForMoviesLoadData(
                        id=writer["id"], full_name=writer["full_name"]
                    )
                    for writer in movie["writers"]
                ],
            ).model_dump()
            for movie in self.data.movies
        ]

    def _transform_persons_data(
        self,
    ) -> list[dict[str, Any]]:
        return [
            PersonLoadData(
                id=person["id"],
                full_name=person["full_name"],
                films=[
                    MovieForPersonLoadData(
                        id=film["id"],
                        roles=film["roles"],
                    )
                    for film in person["films"]
                ],
            ).model_dump()
            for person in self.data.persons
        ]

    def _transform_genres_data(self) -> list[dict[str, Any]]:
        return [
            GenreLoadData(
                id=genre["id"],
                name=genre["name"],
            ).model_dump()
            for genre in self.data.genres
        ]
