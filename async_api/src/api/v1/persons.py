from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import UUID4

from src.api.v1.schemas import Film, FilmForPerson, Person
from src.core.cache import cache
from src.services.films import FilmService, get_film_service
from src.services.persons import PersonService, get_person_service

router = APIRouter(redirect_slashes=False)


@router.get("/search", response_model=list[Person])
@cache()
async def persons_search(
    request: Request,
    query: Annotated[str, Query(description="Search query string", min_length=1)],
    page_size: Annotated[
        int, Query(description="Pagination page size", ge=1, le=100)
    ] = 10,
    page_number: Annotated[int, Query(description="Pagination page number", ge=0)] = 0,
    person_service: PersonService = Depends(get_person_service),
) -> list[Person]:
    """Search for persons by a full name."""
    persons = await person_service.search(
        query=query,
        page_size=page_size,
        page_number=page_number,
    )
    return [
        Person(
            uuid=person.id,
            full_name=person.full_name,
            films=[
                FilmForPerson(uuid=film.id, roles=film.roles) for film in person.films
            ],
        )
        for person in persons
    ]


@router.get("/{person_id}/film", response_model=list[Film])
@cache()
async def person_films(
    request: Request,
    person_id: Annotated[UUID4, Path(description="Person ID")],
    person_service: PersonService = Depends(get_person_service),
    film_service: FilmService = Depends(get_film_service),
) -> list[Film]:
    """Retrieve information about films for a specific person by its ID."""
    person = await person_service.get_by_id(person_id=person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")

    film_ids = [film.id for film in person.films]
    films = await film_service.get_list_by_ids(film_ids=film_ids)

    return [
        Film(
            uuid=film.id,
            title=film.title,
            imdb_rating=film.imdb_rating,
        )
        for film in films
    ]


@router.get("/{person_id}", response_model=Person)
@cache()
async def person_details(
    request: Request,
    person_id: Annotated[UUID4, Path(description="Person ID")],
    person_service: PersonService = Depends(get_person_service),
) -> Person:
    """Retrieve detailed information about a specific person by its ID."""
    person = await person_service.get_by_id(person_id=person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")

    return Person(
        uuid=person.id,
        full_name=person.full_name,
        films=[FilmForPerson(uuid=film.id, roles=film.roles) for film in person.films],
    )
