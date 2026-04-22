import logging
from datetime import UTC, datetime
from uuid import UUID

from pymongo import ReturnDocument

from src.db.mongo import get_client, get_db

logger = logging.getLogger(__name__)

MOVIE = "movie"
REVIEW = "review"


class ReviewNotFoundError(Exception):
    """Raised when review rating operations target a missing review."""


class RatingService:
    def __init__(self) -> None:
        db = get_db()
        self._client = get_client()
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
    ) -> dict:
        async with (
            self._client.start_session() as session,
            await session.start_transaction(),
        ):
            review_id_str = await self._ensure_review_exists(review_id, session=session)
            return await self._upsert(
                str(user_id), REVIEW, review_id_str, value, session=session
            )

    async def remove_review_rating(self, user_id: UUID, review_id: UUID) -> bool:
        async with (
            self._client.start_session() as session,
            await session.start_transaction(),
        ):
            review_id_str = await self._ensure_review_exists(review_id, session=session)
            return await self._delete(
                str(user_id), REVIEW, review_id_str, session=session
            )

    async def get_review_rating(self, user_id: UUID, review_id: UUID) -> dict | None:
        async with (
            self._client.start_session() as session,
            await session.start_transaction(),
        ):
            review_id_str = await self._ensure_review_exists(review_id, session=session)
            return await self._get(str(user_id), REVIEW, review_id_str, session=session)

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
        cursor = await self._col.aggregate(pipeline)
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

    async def _ensure_review_exists(self, review_id: UUID, session=None) -> str:
        review_id_str = str(review_id)
        doc = await self._reviews_col.find_one(
            {"_id": review_id_str}, {"_id": 1}, session=session
        )
        if doc is None:
            raise ReviewNotFoundError()
        return review_id_str

    async def _upsert(
        self, user_id: str, target_type: str, target_id: str, value: int, session=None
    ) -> dict:
        now = datetime.now(UTC)

        return await self._col.find_one_and_update(
            {"user_id": user_id, "target_type": target_type, "target_id": target_id},
            {
                "$set": {"value": value, "updated_at": now},
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
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
