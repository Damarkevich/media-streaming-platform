from pydantic import BaseModel, UUID4


class Genre(BaseModel):
    uuid: UUID4
    name: str


class Person(BaseModel):
    uuid: UUID4
    full_name: str


class Film(BaseModel):
    uuid: UUID4
    title: str
    imdb_rating: float


class FilmDetail(BaseModel):
    uuid: UUID4
    title: str
    imdb_rating: float
    description: str
    genre: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []
