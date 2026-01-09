from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from scr.services.film import FilmService, get_film_service

router = APIRouter()


class Film(BaseModel):
    id: str
    title: str


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
    return Film(id=film.id, title=film.title)
