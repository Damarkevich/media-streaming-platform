import pytest

from src.services.blacklist import HybridBlacklistChecker, get_blacklist_checker


class DummyRedis:
    def __init__(
        self, value: bytes | None = None, error: Exception | None = None
    ) -> None:
        self.value = value
        self.error = error
        self.last_key: str | None = None

    async def get(self, key: str) -> bytes | None:
        self.last_key = key
        if self.error is not None:
            raise self.error
        return self.value


class DummyResult:
    def __init__(self, scalar_value: object | None) -> None:
        self.scalar_value = scalar_value

    def scalar_one_or_none(self) -> object | None:
        return self.scalar_value


class DummySession:
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


class DummySessionContext:
    def __init__(
        self,
        *,
        session: DummySession | None = None,
        enter_error: Exception | None = None,
    ) -> None:
        self.session = session
        self.enter_error = enter_error

    async def __aenter__(self) -> DummySession:
        if self.enter_error is not None:
            raise self.enter_error
        assert self.session is not None
        return self.session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_is_token_revoked_returns_false_for_unknown_token_type() -> None:
    checker = HybridBlacklistChecker()

    result = await checker.is_token_revoked(token_type="custom", jti="jti-1")

    assert result is False


@pytest.mark.asyncio
async def test_access_token_blacklisted_when_key_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = DummyRedis(value=b"true")

    async def _get_redis() -> DummyRedis:
        return redis

    monkeypatch.setattr("src.services.blacklist.get_redis", _get_redis)

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="access", jti="jti-1")

    assert result is True
    assert redis.last_key == "blacklist:access:jti-1"


@pytest.mark.asyncio
async def test_access_token_not_blacklisted_when_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = DummyRedis(value=None)

    async def _get_redis() -> DummyRedis:
        return redis

    monkeypatch.setattr("src.services.blacklist.get_redis", _get_redis)

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="access", jti="jti-2")

    assert result is False


@pytest.mark.asyncio
async def test_access_blacklist_check_fails_closed_on_redis_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = DummyRedis(error=RuntimeError("redis down"))

    async def _get_redis() -> DummyRedis:
        return redis

    monkeypatch.setattr("src.services.blacklist.get_redis", _get_redis)

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="access", jti="jti-3")

    assert result is True


@pytest.mark.asyncio
async def test_refresh_token_blacklisted_when_row_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = DummySession(result=DummyResult(scalar_value=object()))
    monkeypatch.setattr(
        "src.services.blacklist.async_session",
        lambda: DummySessionContext(session=session),
    )

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-4")

    assert result is True


@pytest.mark.asyncio
async def test_refresh_token_not_blacklisted_when_row_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = DummySession(result=DummyResult(scalar_value=None))
    monkeypatch.setattr(
        "src.services.blacklist.async_session",
        lambda: DummySessionContext(session=session),
    )

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-5")

    assert result is False


@pytest.mark.asyncio
async def test_refresh_blacklist_check_fails_closed_on_db_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.services.blacklist.async_session",
        lambda: DummySessionContext(enter_error=RuntimeError("db down")),
    )

    checker = HybridBlacklistChecker()
    result = await checker.is_token_revoked(token_type="refresh", jti="jti-6")

    assert result is True


def test_get_blacklist_checker_returns_singleton() -> None:
    assert get_blacklist_checker() is get_blacklist_checker()
