from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import AfterValidator, BaseModel

from src.core.cache import cache
from src.services.film import FilmService, get_film_service


def validate_sort(sort: str) -> str:
    """Validate sort parameter to ensure it only contains allowed fields."""
    allowed_fields = {"imdb_rating"}

    for field in sort.split(","):
        field_name = field.lstrip("-")
        if field_name not in allowed_fields:
            raise ValueError(
                f"Invalid sort field: {field_name}, allowed fields are: {', '.join(allowed_fields)}"
            )
    return sort


router = APIRouter(redirect_slashes=False)


class Genre(BaseModel):
    uuid: str
    name: str


class Person(BaseModel):
    uuid: str
    full_name: str


class Film(BaseModel):
    uuid: str
    title: str
    imdb_rating: float


class FilmDetail(BaseModel):
    uuid: str
    title: str
    imdb_rating: float
    description: str
    genre: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []


@router.get("/{film_id}", response_model=FilmDetail)
@cache()
async def film_details(
    request: Request,
    film_id: str,
    film_service: FilmService = Depends(get_film_service),
) -> FilmDetail:
    """
    Retrieve detailed information about a specific film by its ID.

    Args:
        film_id (str): The unique identifier of the film to retrieve.
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).

    Returns:
        FilmDetail: A Film object containing detailed information about the film.

    Raises:
        HTTPException: 404 status code if the film with the specified ID is not found.
    """
    film = await film_service.get_by_id(film_id=film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")
    return FilmDetail(
        uuid=film.id,
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description or "",
        genre=[Genre(uuid=g.id, name=g.name) for g in film.genres],
        actors=[Person(uuid=a.id, full_name=a.name) for a in film.actors],
        writers=[Person(uuid=w.id, full_name=w.name) for w in film.writers],
        directors=[Person(uuid=d.id, full_name=d.name) for d in film.directors],
    )


@router.get("", response_model=list[Film])
@cache()
async def film_list(
    request: Request,
    page_size: int = 10,
    page_number: int = 0,
    sort: Annotated[str, AfterValidator(validate_sort)] = "-imdb_rating",
    film_service: FilmService = Depends(get_film_service),
) -> list[Film]:
    """
    Retrieve a paginated list of films.

    Args:
        page_size (int, optional): The number of films to return per page. Defaults to 10.
        page_number (int, optional): The page number to retrieve. Defaults to 0.
        sort (str, optional): A comma-separated string of fields to sort by.
                              Prefix a field with '-' for descending order. Defaults to '-imdb_rating'.
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).

    Returns:
        list[Film]: A list of Film objects.
    """
    films = await film_service.get_list(
        page_size=page_size,
        page_number=page_number,
        sort=sort,
    )
    data = [
        Film(uuid=film.id, title=film.title, imdb_rating=film.imdb_rating)
        for film in films
    ]
    return data
