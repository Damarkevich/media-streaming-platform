from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import UUID4, AfterValidator

from src.api.v1.paginators import PaginationParams
from src.api.v1.schemas import Film, FilmDetail, Genre, PersonForFilm
from src.api.v1.validators import validate_sort
from src.core.cache import cache
from src.services.films import FilmService, get_film_service

router = APIRouter(redirect_slashes=False)


@router.get("", response_model=list[Film])
@cache()
async def films_list(
    request: Request,  # noqa: ARG001
    sort: Annotated[str, AfterValidator(validate_sort)] = "-imdb_rating",
    genre: Annotated[UUID4 | None, Query(description="Filter by genre ID")] = None,
    pagination: PaginationParams = Depends(PaginationParams),  # noqa: B008
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> list[Film]:
    """Retrieve a paginated list of films with optional sorting and genre filtering."""
    films = await film_service.get_list(
        page_size=pagination.page_size,
        page_number=pagination.page_number,
        sort=sort,
        genre_id=genre,
    )

    return [
        Film(uuid=film.id, title=film.title, imdb_rating=film.imdb_rating)
        for film in films
    ]


@router.get("/search", response_model=list[Film])
@cache()
async def films_search(
    request: Request,  # noqa: ARG001
    query: Annotated[str, Query(description="Search query string", min_length=1)],
    pagination: PaginationParams = Depends(PaginationParams),  # noqa: B008
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> list[Film]:
    """Search for films by title and description."""
    films = await film_service.search(
        query=query,
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )

    return [
        Film(uuid=film.id, title=film.title, imdb_rating=film.imdb_rating)
        for film in films
    ]


@router.get("/{film_id}", response_model=FilmDetail)
@cache()
async def film_details(
    request: Request,  # noqa: ARG001
    film_id: Annotated[UUID4, Path(description="The ID of the film to retrieve")],
    film_service: FilmService = Depends(get_film_service),  # noqa: B008
) -> FilmDetail:
    """Retrieve detailed information about a specific film by its ID."""
    film = await film_service.get_by_id(film_id=film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="film not found")

    return FilmDetail(
        uuid=film.id,
        title=film.title,
        imdb_rating=film.imdb_rating,
        description=film.description,
        genre=[Genre(uuid=g.id, name=g.name) for g in film.genres],
        actors=[PersonForFilm(uuid=a.id, full_name=a.full_name) for a in film.actors],
        writers=[PersonForFilm(uuid=w.id, full_name=w.full_name) for w in film.writers],
        directors=[
            PersonForFilm(uuid=d.id, full_name=d.full_name) for d in film.directors
        ],
    )
