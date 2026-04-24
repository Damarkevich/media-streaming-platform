import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pymongo import ReturnDocument

from src.db.mongo import get_client, get_db

logger = logging.getLogger(__name__)
REVIEW = "review"


def _fmt(doc: dict) -> dict:
    """Normalize Mongo _id field to public id field for API serialization."""
    doc["id"] = str(doc.pop("_id"))
    return doc


class ReviewService:
    def __init__(self) -> None:
        db = get_db()
        self._client = get_client()
        self._col = db.reviews
        self._ratings_col = db.ratings

    async def upsert(self, user_id: UUID, movie_id: UUID, text: str) -> dict:
        """Create or update the single review this user has for the movie."""
        now = datetime.now(UTC)
        doc = await self._col.find_one_and_update(
            {"user_id": str(user_id), "movie_id": str(movie_id)},
            {
                "$set": {"text": text, "updated_at": now},
                "$setOnInsert": {
                    "_id": str(uuid4()),
                    "user_id": str(user_id),
                    "movie_id": str(movie_id),
                    "created_at": now,
                    "rating_count": 0,
                    "rating_sum": 0.0,
                    "rating_avg": None,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return _fmt(doc)

    async def delete(self, user_id: UUID, movie_id: UUID) -> bool:
        async with (
            self._client.start_session() as session,
            await session.start_transaction(),
        ):
            review = await self._col.find_one(
                {"user_id": str(user_id), "movie_id": str(movie_id)},
                {"_id": 1},
                session=session,
            )
            if review is None:
                return False

            await self._col.delete_one(
                {"user_id": str(user_id), "movie_id": str(movie_id)},
                session=session,
            )
            await self._ratings_col.delete_many(
                {"target_type": REVIEW, "target_id": review["_id"]},
                session=session,
            )
            return True

    async def get_my_review(self, user_id: UUID, movie_id: UUID) -> dict | None:
        doc = await self._col.find_one(
            {"user_id": str(user_id), "movie_id": str(movie_id)}
        )
        return _fmt(doc) if doc else None

    async def get_review_by_id(self, review_id: UUID) -> dict | None:
        doc = await self._col.find_one({"_id": str(review_id)})
        return _fmt(doc) if doc else None

    async def list_for_movie(
        self,
        movie_id: UUID,
        sort: str = "-created_at",
        page_size: int = 10,
        page_number: int = 0,
    ) -> list[dict]:
        sort_map: dict[str, dict[str, int]] = {
            "-created_at": {"created_at": -1},
            "created_at": {"created_at": 1},
            "-rating_avg": {"rating_avg": -1, "created_at": -1},
            "rating_avg": {"rating_avg": 1, "created_at": -1},
        }
        pipeline = [
            {"$match": {"movie_id": str(movie_id)}},
            {"$sort": sort_map[sort]},
            {"$skip": page_number * page_size},
            {"$limit": page_size},
        ]

        cursor = self._col.aggregate(pipeline)
        docs = await cursor.to_list(length=page_size)
        return [_fmt(d) for d in docs]


def get_review_service() -> ReviewService:
    return ReviewService()
