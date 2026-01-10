from fastapi import APIRouter, Depends, Request

from src.api.v1.schemas import Genre
from src.core.cache import cache
from src.services.genre import GenreService, get_genre_service

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=list[Genre])
@cache()
async def genres_list(
    request: Request,
    genre_service: GenreService = Depends(get_genre_service),
) -> list[Genre]:
    """
    Retrieve a list of genres.

    Args:
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).

    Returns:
        list[Genre]: A list of Genre objects.
    """
    genres = await genre_service.get_list()
    data = [Genre(uuid=genre.id, name=genre.name) for genre in genres]
    return data
