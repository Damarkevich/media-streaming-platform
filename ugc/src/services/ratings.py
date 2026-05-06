import logging
from datetime import UTC, datetime
from uuid import UUID

from pymongo import ReturnDocument

from src.core.kafka import publish
from src.db.mongo import get_db

logger = logging.getLogger(__name__)

MOVIE = "movie"
REVIEW = "review"
REVIEW_LIKED_TOPIC = "notifications.events.review_liked"
LIKE_VALUE = 10


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
        # Fire-and-forget notification when a user likes a review (value == 10)
        if value == LIKE_VALUE:
            await self._publish_review_liked(str(user_id), review_id_str)
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

    async def _publish_review_liked(self, liker_user_id: str, review_id: str) -> None:
        """Fetch review author and publish review_liked event to Kafka."""
        try:
            doc = await self._reviews_col.find_one({"_id": review_id}, {"user_id": 1})
            if doc is None:
                return
            review_author_id: str = doc["user_id"]
            # Don't notify someone that they liked their own review
            if review_author_id == liker_user_id:
                return
            publish(
                REVIEW_LIKED_TOPIC,
                key=f"review_liked:{review_id}:{liker_user_id}",
                payload={
                    "review_id": review_id,
                    "review_author_id": review_author_id,
                    "liker_user_id": liker_user_id,
                },
            )
        except Exception:
            logger.exception(
                "Failed to publish review_liked event for review %s", review_id
            )

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
        """Atomically increment rating_count/rating_sum and recompute rating_avg.

        Uses a single aggregation-pipeline update (MongoDB 4.2+) so that
        rating_avg is always consistent with the post-increment count/sum values,
        eliminating the two-write race present in the previous implementation.
        """
        await self._reviews_col.update_one(
            {"_id": review_id},
            [
                {
                    "$set": {
                        "rating_count": {"$add": ["$rating_count", count_delta]},
                        "rating_sum": {"$add": ["$rating_sum", sum_delta]},
                    }
                },
                {
                    "$set": {
                        "rating_avg": {
                            "$cond": {
                                "if": {"$gt": ["$rating_count", 0]},
                                "then": {"$divide": ["$rating_sum", "$rating_count"]},
                                "else": None,
                            }
                        }
                    }
                },
            ],
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
