import logging
from datetime import UTC, datetime
from uuid import UUID

from pymongo import ReturnDocument

from src.db.mongo import get_db

logger = logging.getLogger(__name__)


class BookmarkService:
    def __init__(self) -> None:
        self._col = get_db().bookmarks

    async def add(self, user_id: UUID, movie_id: UUID) -> dict:
        """Upsert bookmark; return document."""
        return await self._col.find_one_and_update(
            {"user_id": str(user_id), "movie_id": str(movie_id)},
            {
                "$setOnInsert": {
                    "user_id": str(user_id),
                    "movie_id": str(movie_id),
                    "created_at": datetime.now(UTC),
                }
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    async def remove(self, user_id: UUID, movie_id: UUID) -> bool:
        result = await self._col.delete_one(
            {"user_id": str(user_id), "movie_id": str(movie_id)}
        )
        return result.deleted_count > 0

    async def list_for_user(
        self, user_id: UUID, page_size: int = 10, page_number: int = 0
    ) -> list[dict]:
        cursor = (
            self._col.find({"user_id": str(user_id)})
            .sort("created_at", -1)
            .skip(page_number * page_size)
            .limit(page_size)
        )
        return await cursor.to_list(length=page_size)


def get_bookmark_service() -> BookmarkService:
    return BookmarkService()
