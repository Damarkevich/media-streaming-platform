from pydantic import BaseModel


class Genre(BaseModel):
    id: str
    name: str


class Person(BaseModel):
    id: str
    name: str


class Film(BaseModel):
    id: str
    title: str
    imdb_rating: float
    description: str | None = None
    genres: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []
