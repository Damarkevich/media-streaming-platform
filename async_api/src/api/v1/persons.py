from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import AfterValidator, UUID4

from src.api.v1.schemas import Film, FilmDetail, FilmForPerson, Genre, Person
from src.core.cache import cache
from src.services.persons import PersonService, get_person_service
from src.services.films import FilmService, get_film_service

router = APIRouter(redirect_slashes=False)


# @router.get("", response_model=list[Film])
# @cache()
# async def films_list(
#     request: Request,
#     page_size: int = 10,
#     page_number: int = 0,
#     sort: Annotated[str, AfterValidator(validate_sort)] = "-imdb_rating",
#     genre: UUID4 | None = None,
#     film_service: FilmService = Depends(get_film_service),
# ) -> list[Film]:
#     """
#     Retrieve a paginated list of films.

#     Args:
#         page_size (int, optional): The number of films to return per page. Defaults to 10.
#         page_number (int, optional): The page number to retrieve. Defaults to 0.
#         sort (str, optional): A comma-separated string of fields to sort by.
#                               Prefix a field with '-' for descending order. Defaults to '-imdb_rating'.
#         genre (UUID4 | None, optional): Filter films by genre ID. Defaults to None.
#         film_service (FilmService, optional): The film service dependency for data access.
#             Defaults to Depends(get_film_service).

#     Returns:
#         list[Film]: A list of Film objects.
#     """
#     films = await film_service.get_list(
#         page_size=page_size,
#         page_number=page_number,
#         sort=sort,
#         genre=genre,
#     )
#     data = [
#         Film(uuid=film.id, title=film.title, imdb_rating=film.imdb_rating)
#         for film in films
#     ]
#     return data


@router.get("/search", response_model=list[Person])
@cache()
async def persons_search(
    request: Request,
    query: str,
    page_size: int = 10,
    page_number: int = 0,
    person_service: PersonService = Depends(get_person_service),
) -> list[Person]:
    """
    Search for persons by a query string.

    Args:
        query (str): The search query string.
        page_size (int, optional): The number of films to return per page. Defaults to 10.
        page_number (int, optional): The page number to retrieve. Defaults to 0.
        person_service (PersonService, optional): The person service dependency for data access.
            Defaults to Depends(get_person_service).

    Returns:
        list[Person]: A list of Person objects matching the search query.
    """
    persons = await person_service.search(
        query=query,
        page_size=page_size,
        page_number=page_number,
    )
    print(persons)
    data = [
        Person(
            uuid=person.id,
            full_name=person.full_name,
            films=[
                FilmForPerson(uuid=film.id, roles=film.roles) for film in person.films
            ],
        )
        for person in persons
    ]
    return data


@router.get("/{person_id}/film", response_model=list[Film])
@cache()
async def person_films(
    request: Request,
    person_id: UUID4,
    person_service: PersonService = Depends(get_person_service),
    film_service: FilmService = Depends(get_film_service),
) -> list[Film]:
    """
    Retrieve information about films for a specific person by its ID.

    Args:
        person_id (UUID4): The unique identifier of the person to retrieve films for.
        film_service (FilmService, optional): The film service dependency for data access.
            Defaults to Depends(get_film_service).
        person_service (PersonService, optional): The person service dependency for data access.
            Defaults to Depends(get_person_service).

    Returns:
        list[Film]: A list of Film objects containing information about the films for the person.

    Raises:
        HTTPException: 404 status code if the person with the specified ID is not found.
    """
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
    person_id: UUID4,
    person_service: PersonService = Depends(get_person_service),
) -> Person:
    """
    Retrieve detailed information about a specific person by its ID.

    Args:
        person_id (UUID4): The unique identifier of the person to retrieve.
        person_service (PersonService, optional): The person service dependency for data access.
            Defaults to Depends(get_person_service).

    Returns:
        Person: A Person object containing detailed information about the person.

    Raises:
        HTTPException: 404 status code if the person with the specified ID is not found.
    """
    person = await person_service.get_by_id(person_id=person_id)
    if not person:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="person not found")
    return Person(
        uuid=person.id,
        full_name=person.full_name,
        films=[FilmForPerson(uuid=film.id, roles=film.roles) for film in person.films],
    )
