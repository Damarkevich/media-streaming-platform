import logging
from datetime import UTC, datetime
from uuid import UUID

from pymongo import ReturnDocument

from src.db.mongo import get_db

logger = logging.getLogger(__name__)

MOVIE = "movie"
REVIEW = "review"


class ReviewNotFoundError(Exception):
    """Raised when review rating operations target a missing review."""


class RatingService:
    def __init__(self) -> None:
        db = get_db()
        self._col = db.ratings
        self._reviews_col = db.reviews

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def set_movie_rating(self, user_id: UUID, movie_id: UUID, value: int) -> dict:
        return await self._upsert(str(user_id), MOVIE, str(movie_id), value)

    async def remove_movie_rating(self, user_id: UUID, movie_id: UUID) -> bool:
        return await self._delete(str(user_id), MOVIE, str(movie_id))

    async def get_movie_rating(self, user_id: UUID, movie_id: UUID) -> dict | None:
        return await self._get(str(user_id), MOVIE, str(movie_id))

    async def set_review_rating(
        self, user_id: UUID, review_id: UUID, value: int
    ) -> dict | None:
        review_id_str = await self._ensure_review_exists(review_id)
        # Use BEFORE to atomically learn the previous state: None means insert,
        # a document means update — eliminating the separate _get + upsert race.
        before = await self._upsert(
            str(user_id),
            REVIEW,
            review_id_str,
            value,
            return_document=ReturnDocument.BEFORE,
        )
        after = await self._get(str(user_id), REVIEW, review_id_str)
        if before is None:
            count_delta, sum_delta = 1, float(value)
        else:
            count_delta, sum_delta = 0, float(value - before["value"])
        await self._update_review_stats(review_id_str, count_delta, sum_delta)
        return after

    async def remove_review_rating(self, user_id: UUID, review_id: UUID) -> bool:
        review_id_str = await self._ensure_review_exists(review_id)
        existing = await self._get(str(user_id), REVIEW, review_id_str)
        removed = await self._delete(str(user_id), REVIEW, review_id_str)
        if removed and existing is not None:
            await self._update_review_stats(
                review_id_str, -1, -float(existing["value"])
            )
        return removed

    async def get_review_rating(self, user_id: UUID, review_id: UUID) -> dict | None:
        review_id_str = await self._ensure_review_exists(review_id)
        return await self._get(str(user_id), REVIEW, review_id_str)

    async def get_movie_stats(self, movie_id: UUID) -> dict:
        pipeline = [
            {
                "$match": {
                    "target_type": MOVIE,
                    "target_id": str(movie_id),
                }
            },
            {
                "$group": {
                    "_id": None,
                    "rating_count": {"$sum": 1},
                    "rating_avg": {"$avg": "$value"},
                }
            },
        ]
        cursor = self._col.aggregate(pipeline)
        docs = await cursor.to_list(length=1)
        if not docs:
            return {"rating_avg": None, "rating_count": 0}
        return {
            "rating_avg": docs[0].get("rating_avg"),
            "rating_count": docs[0].get("rating_count", 0),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get(
        self, user_id: str, target_type: str, target_id: str, session=None
    ) -> dict | None:
        return await self._col.find_one(
            {"user_id": user_id, "target_type": target_type, "target_id": target_id},
            session=session,
        )

    async def _update_review_stats(
        self, review_id: str, count_delta: int, sum_delta: float, session=None
    ) -> None:
        """Increment denormalized rating_count/rating_sum on the review and recompute rating_avg."""
        doc = await self._reviews_col.find_one_and_update(
            {"_id": review_id},
            {"$inc": {"rating_count": count_delta, "rating_sum": sum_delta}},
            return_document=ReturnDocument.AFTER,
            session=session,
        )
        if doc is not None:
            count = doc.get("rating_count", 0)
            total = doc.get("rating_sum", 0.0)
            avg = total / count if count > 0 else None
            await self._reviews_col.update_one(
                {"_id": review_id},
                {"$set": {"rating_avg": avg}},
                session=session,
            )

    async def _ensure_review_exists(self, review_id: UUID, session=None) -> str:
        review_id_str = str(review_id)
        doc = await self._reviews_col.find_one(
            {"_id": review_id_str}, {"_id": 1}, session=session
        )
        if doc is None:
            raise ReviewNotFoundError()
        return review_id_str

    async def _upsert(
        self,
        user_id: str,
        target_type: str,
        target_id: str,
        value: int,
        return_document: ReturnDocument = ReturnDocument.AFTER,
        session=None,
    ) -> dict | None:
        now = datetime.now(UTC)

        return await self._col.find_one_and_update(
            {"user_id": user_id, "target_type": target_type, "target_id": target_id},
            {
                "$set": {"value": value, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=return_document,
            session=session,
        )

    async def _delete(
        self, user_id: str, target_type: str, target_id: str, session=None
    ) -> bool:
        deleted_doc = await self._col.find_one_and_delete(
            {"user_id": user_id, "target_type": target_type, "target_id": target_id},
            session=session,
        )
        return deleted_doc is not None


def get_rating_service() -> RatingService:
    return RatingService()
