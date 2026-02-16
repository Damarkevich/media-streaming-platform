from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import UUID4

from src.api.v1.paginators import PaginationParams
from src.api.v1.schemas import Genre
from src.core.cache import cache
from src.services.genres import GenreService, get_genre_service

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=list[Genre])
@cache()
async def genres_list(
    request: Request,
    pagination: PaginationParams = Depends(PaginationParams),
    genre_service: GenreService = Depends(get_genre_service),
) -> list[Genre]:
    """Retrieve a list of genres."""
    genres = await genre_service.get_list(
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )

    return [Genre(uuid=genre.id, name=genre.name) for genre in genres]


@router.get("/{genre_id}", response_model=Genre)
@cache()
async def genre_detail(
    request: Request,
    genre_id: Annotated[UUID4, Path(description="Genre ID")],
    genre_service: GenreService = Depends(get_genre_service),
) -> Genre:
    """Retrieve detailed information about a specific genre by its ID."""
    genre = await genre_service.get_by_id(genre_id)
    if not genre:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="genre not found")

    return Genre(uuid=genre.id, name=genre.name)
