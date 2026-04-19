"""Pydantic schemas for the UGC service API."""

from datetime import datetime
from enum import IntEnum
from typing import Literal

from pydantic import UUID4, BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class RatingValue(IntEnum):
    dislike = 0
    like = 10


TargetType = Literal["movie", "review"]


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------


class BookmarkOut(BaseModel):
    movie_id: UUID4
    created_at: datetime


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


class RatingIn(BaseModel):
    value: RatingValue


class RatingOut(BaseModel):
    target_type: TargetType
    target_id: UUID4
    value: RatingValue
    created_at: datetime
    updated_at: datetime


class RatingStats(BaseModel):
    rating_avg: float | None
    rating_count: int


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------


class ReviewIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)


class ReviewOut(BaseModel):
    id: UUID4
    user_id: UUID4
    movie_id: UUID4
    text: str
    created_at: datetime
    updated_at: datetime
    rating_avg: float | None
    rating_count: int
