from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import UUID4

from src.api.v1.paginators import PaginationParams
from src.api.v1.schemas import BookmarkOut
from src.core.authorization import require_ugc_access
from src.core.token_models import TokenPayload
from src.services.bookmarks import BookmarkService, get_bookmark_service

router = APIRouter(redirect_slashes=False)


@router.put(
    "/movies/{movie_id}/bookmark", response_model=BookmarkOut, status_code=HTTPStatus.OK
)
async def add_bookmark(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: BookmarkService = Depends(get_bookmark_service),  # noqa: B008
) -> BookmarkOut:
    """Add a movie to the current user's bookmarks (idempotent)."""
    doc = await service.add(user_id=token.sub, movie_id=movie_id)
    return BookmarkOut(movie_id=doc["movie_id"], created_at=doc["created_at"])


@router.delete("/movies/{movie_id}/bookmark", status_code=HTTPStatus.NO_CONTENT)
async def remove_bookmark(
    movie_id: Annotated[UUID4, Path()],
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    service: BookmarkService = Depends(get_bookmark_service),  # noqa: B008
) -> None:
    """Remove a movie from the current user's bookmarks."""
    removed = await service.remove(user_id=token.sub, movie_id=movie_id)
    if not removed:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Bookmark not found."
        )


@router.get("/bookmarks", response_model=list[BookmarkOut])
async def list_bookmarks(
    token: Annotated[TokenPayload, Depends(require_ugc_access)],
    pagination: PaginationParams = Depends(PaginationParams),  # noqa: B008
    service: BookmarkService = Depends(get_bookmark_service),  # noqa: B008
) -> list[BookmarkOut]:
    """List bookmarks for the current user, newest first."""
    docs = await service.list_for_user(
        user_id=token.sub,
        page_size=pagination.page_size,
        page_number=pagination.page_number,
    )
    return [
        BookmarkOut(movie_id=d["movie_id"], created_at=d["created_at"]) for d in docs
    ]
