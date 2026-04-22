from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel
from pymongo.asynchronous.database import AsyncDatabase

from src.core.config import settings

client: AsyncMongoClient | None = None


def get_client() -> AsyncMongoClient:
    if client is None:
        msg = "MongoDB client is not initialized"
        raise RuntimeError(msg)
    return client


def get_db() -> AsyncDatabase:
    return get_client()[settings.mongodb_database]


async def ensure_indexes() -> None:
    """Create required indexes for all collections."""
    database = get_db()

    # bookmarks: unique (user_id, movie_id); list by user ordered by date
    await database.bookmarks.create_indexes(
        [
            IndexModel([("user_id", ASCENDING), ("movie_id", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        ]
    )

    # ratings: unique (user_id, target_type, target_id); lookup by target
    await database.ratings.create_indexes(
        [
            IndexModel(
                [
                    ("user_id", ASCENDING),
                    ("target_type", ASCENDING),
                    ("target_id", ASCENDING),
                ],
                unique=True,
            ),
            IndexModel([("target_type", ASCENDING), ("target_id", ASCENDING)]),
            IndexModel(
                [
                    ("target_type", ASCENDING),
                    ("target_id", ASCENDING),
                    ("value", ASCENDING),
                ]
            ),
        ]
    )

    # reviews: unique (user_id, movie_id); list by movie ordered by date
    await database.reviews.create_indexes(
        [
            IndexModel([("user_id", ASCENDING), ("movie_id", ASCENDING)], unique=True),
            IndexModel([("movie_id", ASCENDING), ("created_at", DESCENDING)]),
        ]
    )


async def check_mongo() -> bool:
    """Check MongoDB write readiness for transactional workloads."""
    try:
        if client is None:
            return False

        hello = await client.admin.command("hello")
        # Transactional write paths require a writable primary in a replica set.
        if not hello.get("isWritablePrimary", False):
            return False
        return bool(hello.get("setName"))
    except Exception:
        return False
