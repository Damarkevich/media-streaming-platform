from pydantic import UUID4, BaseModel


class Genre(BaseModel):
    id: UUID4
    name: str


class PersonForFilm(BaseModel):
    id: UUID4
    full_name: str


class Film(BaseModel):
    id: UUID4
    title: str
    imdb_rating: float
    description: str
    genres: list[Genre] = []
    actors: list[PersonForFilm] = []
    writers: list[PersonForFilm] = []
    directors: list[PersonForFilm] = []


class FilmForPerson(BaseModel):
    id: UUID4
    roles: list[str] = []


class Person(BaseModel):
    id: UUID4
    full_name: str
    films: list[FilmForPerson] = []
