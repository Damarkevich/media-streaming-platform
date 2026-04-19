from http import HTTPStatus
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import UUID4

from src.api.v1.paginators import PaginationParams
from src.api.v1.schemas import ReviewIn, ReviewOut
from src.core.authorization import require_ugc_access
from src.core.token_models import TokenPayload
from src.services.reviews import ReviewService, get_review_service

router = APIRouter(redirect_slashes=False)


@router.put("/movies/{movie_id}/review", response_model=ReviewOut)
async def upsert_review(
    movie_id: Annotated[UUID4, Path()],
    body: ReviewIn,
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    """Create or update the current user's review for a movie (one review per user per movie)."""
    doc = await service.upsert(user_id=token.sub, movie_id=movie_id, text=body.text)
    return ReviewOut(**doc)


@router.delete("/movies/{movie_id}/review", status_code=HTTPStatus.NO_CONTENT)
async def delete_review(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: ReviewService = Depends(get_review_service),
) -> None:
    """Delete the current user's review for a movie."""
    removed = await service.delete(user_id=token.sub, movie_id=movie_id)
    if not removed:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        )


@router.get("/movies/{movie_id}/review/my", response_model=ReviewOut)
async def get_my_review(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    """Get the current user's review for a movie."""
    doc = await service.get_my_review(user_id=token.sub, movie_id=movie_id)
    if not doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        )
    return ReviewOut(**doc)


@router.get("/movies/{movie_id}/reviews", response_model=list[ReviewOut])
async def list_movie_reviews(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    sort: Annotated[
        Literal["-created_at", "created_at", "-rating_avg", "rating_avg"],
        Query(description="Sort by creation date or rating average"),
    ] = "-created_at",
    pagination: PaginationParams = Depends(PaginationParams),
    service: ReviewService = Depends(get_review_service),
) -> list[ReviewOut]:
    """List all reviews for a movie with sorting by date or rating."""
    docs = await service.list_for_movie(
        movie_id=movie_id,
        sort=sort,
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )
    return [ReviewOut(**d) for d in docs]


@router.get("/reviews/{review_id}", response_model=ReviewOut)
async def get_review(
    review_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: ReviewService = Depends(get_review_service),
) -> ReviewOut:
    """Get a single review by its ID."""
    doc = await service.get_review_by_id(review_id=review_id)
    if not doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        )
    return ReviewOut(**doc)
