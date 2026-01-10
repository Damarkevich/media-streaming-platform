from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.services.film import FilmService, get_film_service

router = APIRouter()


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
    description: str | None = None
    genre: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []


@router.get("/{film_id}", response_model=Film)
async def film_details(
    film_id: str, film_service: FilmService = Depends(get_film_service)
) -> Film:
    """
    Retrieve detailed information about a specific film by its ID.

    Args:
        film_id (str): The unique identifier of the film to retrieve.
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).

    Returns:
        Film: A Film object containing the film's id and title.

    Raises:
        HTTPException: 404 status code if the film with the specified ID is not found.
    """
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")
    return Film(
        uuid=film.id,
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genre=[Genre(uuid=g.id, name=g.name) for g in film.genres],
        actors=[Person(uuid=a.id, full_name=a.name) for a in film.actors],
        writers=[Person(uuid=w.id, full_name=w.name) for w in film.writers],
        directors=[Person(uuid=d.id, full_name=d.name) for d in film.directors],
    )


@router.get("/", response_model=list[Film])
async def film_list(
    page_size: int = 50,
    page_number: int = 0,
    film_service: FilmService = Depends(get_film_service),
) -> list[Film]:
    """
    Retrieve a paginated list of films.

    Args:
        page_size (int, optional): The number of films to return per page. Defaults to 50.
        page_number (int, optional): The page number to retrieve. Defaults to 0.
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).

    Returns:
        list[Film]: A list of Film objects.
    """
    films = await film_service.get_list(page_size, page_number)
    return [Film(id=film.id, title=film.title) for film in films]
