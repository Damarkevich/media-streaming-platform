from pydantic import UUID4, BaseModel


class Genre(BaseModel):
    id: UUID4
    name: str


class Person(BaseModel):
    id: UUID4
    name: str


class Film(BaseModel):
    id: UUID4
    title: str
    imdb_rating: float
    description: str | None = None
    genres: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []
