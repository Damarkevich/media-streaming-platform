from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import UUID4

from src.api.v1.schemas import RatingIn, RatingOut, RatingStats
from src.core.authorization import require_ugc_access
from src.core.token_models import TokenPayload
from src.services.ratings import RatingService, ReviewNotFoundError, get_rating_service

router = APIRouter(redirect_slashes=False)


# ---------------------------------------------------------------------------
# Movie ratings
# ---------------------------------------------------------------------------


@router.put("/movies/{movie_id}/rating", response_model=RatingOut)
async def set_movie_rating(
    movie_id: Annotated[UUID4, Path()],
    body: RatingIn,
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> RatingOut:
    """Set or update the current user's rating for a movie (like=10, dislike=0)."""
    doc = await service.set_movie_rating(
        user_id=token.sub, movie_id=movie_id, value=body.value
    )
    return RatingOut(
        target_type="movie",
        target_id=doc["target_id"],
        value=doc["value"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.delete("/movies/{movie_id}/rating", status_code=HTTPStatus.NO_CONTENT)
async def remove_movie_rating(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> None:
    """Revoke the current user's rating for a movie."""
    removed = await service.remove_movie_rating(user_id=token.sub, movie_id=movie_id)
    if not removed:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Rating not found."
        )


@router.get("/movies/{movie_id}/rating", response_model=RatingStats)
async def get_movie_rating_stats(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],  # noqa: ARG001
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> RatingStats:
    """Get aggregated rating stats for a movie."""
    stats = await service.get_movie_stats(movie_id=movie_id)
    return RatingStats(**stats)


@router.get("/movies/{movie_id}/rating/my", response_model=RatingOut)
async def get_my_movie_rating(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> RatingOut:
    """Get the current user's rating for a movie."""
    doc = await service.get_movie_rating(user_id=token.sub, movie_id=movie_id)
    if not doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Rating not found."
        )
    return RatingOut(
        target_type="movie",
        target_id=doc["target_id"],
        value=doc["value"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


# ---------------------------------------------------------------------------
# Review ratings
# ---------------------------------------------------------------------------


@router.put("/reviews/{review_id}/rating", response_model=RatingOut)
async def set_review_rating(
    review_id: Annotated[UUID4, Path()],
    body: RatingIn,
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> RatingOut:
    """Set or update the current user's rating for a review (like=10, dislike=0)."""
    try:
        doc = await service.set_review_rating(
            user_id=token.sub, review_id=review_id, value=body.value
        )
    except ReviewNotFoundError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        ) from e
    return RatingOut(
        target_type="review",
        target_id=doc["target_id"],
        value=doc["value"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


@router.delete("/reviews/{review_id}/rating", status_code=HTTPStatus.NO_CONTENT)
async def remove_review_rating(
    review_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> None:
    """Revoke the current user's rating for a review."""
    try:
        removed = await service.remove_review_rating(
            user_id=token.sub, review_id=review_id
        )
    except ReviewNotFoundError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        ) from e
    if not removed:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Rating not found."
        )


@router.get("/reviews/{review_id}/rating/my", response_model=RatingOut)
async def get_my_review_rating(
    review_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: RatingService = Depends(get_rating_service),  # noqa: B008
) -> RatingOut:
    """Get the current user's rating for a review."""
    try:
        doc = await service.get_review_rating(user_id=token.sub, review_id=review_id)
    except ReviewNotFoundError as e:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Review not found."
        ) from e
    if not doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Rating not found."
        )
    return RatingOut(
        target_type="review",
        target_id=doc["target_id"],
        value=doc["value"],
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )
