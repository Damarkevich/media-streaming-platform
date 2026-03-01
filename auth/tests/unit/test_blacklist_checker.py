from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.blacklist import HybridBlacklistChecker
from src.services.redis import RedisClient


class DummyRedisClient:
    """Redis blacklist stub with configurable behavior."""

    def __init__(self, *, value: bool = False, error: Exception | None = None) -> None:
        self.value = value
        self.error = error
        self.last_jti: str | None = None

    async def is_access_token_blacklisted(self, jti: str) -> bool:
        self.last_jti = jti
        if self.error is not None:
            raise self.error
        return self.value


class DummyResult:
    """Scalar SQLAlchemy-like result stub."""

    def __init__(self, scalar_value: object | None) -> None:
        self.scalar_value = scalar_value

    def scalar_one_or_none(self) -> object | None:
        return self.scalar_value


class DummySession:
    """Database session stub with configurable execution outcome."""

    def __init__(
        self, result: DummyResult | None = None, error: Exception | None = None
    ) -> None:
        self.result = result
        self.error = error

    async def execute(self, _query: object) -> DummyResult:
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.mark.asyncio
async def test_is_token_revoked_returns_false_for_unknown_token_type() -> None:
    """Ensure unknown token types are treated as not revoked."""
    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, DummyRedisClient()),
        db=cast(AsyncSession, DummySession()),
    )

    result = await checker.is_token_revoked(token_type="custom", jti="jti-1")

    assert result is False


@pytest.mark.asyncio
async def test_access_token_blacklisted_when_key_exists() -> None:
    """Ensure access token is marked revoked when Redis key exists."""
    redis_client = DummyRedisClient(value=True)

    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, redis_client),
        db=cast(AsyncSession, DummySession()),
    )
    result = await checker.is_token_revoked(token_type="access", jti="jti-1")

    assert result is True
    assert redis_client.last_jti == "jti-1"


@pytest.mark.asyncio
async def test_access_token_not_blacklisted_when_key_missing() -> None:
    """Ensure access token is not revoked when Redis key is absent."""
    redis_client = DummyRedisClient(value=False)

    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, redis_client),
        db=cast(AsyncSession, DummySession()),
    )
    result = await checker.is_token_revoked(token_type="access", jti="jti-2")

    assert result is False


@pytest.mark.asyncio
async def test_access_blacklist_check_fails_closed_on_redis_error() -> None:
    """Ensure Redis failures are treated as revoked tokens."""
    redis_client = DummyRedisClient(error=RuntimeError("redis down"))

    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, redis_client),
        db=cast(AsyncSession, DummySession()),
    )
    result = await checker.is_token_revoked(token_type="access", jti="jti-3")

    assert result is True


@pytest.mark.asyncio
async def test_refresh_token_blacklisted_when_row_exists() -> None:
    """Ensure refresh token is revoked when DB record exists."""
    session = DummySession(result=DummyResult(scalar_value=object()))
    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, DummyRedisClient()),
        db=cast(AsyncSession, session),
    )
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-4")

    assert result is True


@pytest.mark.asyncio
async def test_refresh_token_not_blacklisted_when_row_missing() -> None:
    """Ensure refresh token is not revoked when DB record is absent."""
    session = DummySession(result=DummyResult(scalar_value=None))
    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, DummyRedisClient()),
        db=cast(AsyncSession, session),
    )
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-5")

    assert result is False


@pytest.mark.asyncio
async def test_refresh_blacklist_check_fails_closed_on_db_error() -> None:
    """Ensure DB failures are treated as revoked refresh tokens."""
    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, DummyRedisClient()),
        db=cast(AsyncSession, DummySession(error=RuntimeError("db down"))),
    )
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-6")

    assert result is True


def test_checker_is_constructed_with_injected_dependencies() -> None:
    """Ensure checker can be instantiated with injected dependencies."""
    checker = HybridBlacklistChecker(
        redis_client=cast(RedisClient, DummyRedisClient()),
        db=cast(AsyncSession, DummySession()),
    )
    assert isinstance(checker, HybridBlacklistChecker)
