from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from async_fastapi_jwt_auth import AuthJWT

import src.core.jwt as jwt_module


class DummyChecker:
    """Revocation checker stub used by JWT callback tests."""

    def __init__(self, return_value: bool) -> None:
        self.return_value = return_value
        self.calls: list[tuple[str, str]] = []

    async def is_token_revoked(self, token_type: str, jti: str) -> bool:
        self.calls.append((token_type, jti))
        return self.return_value


@pytest.mark.asyncio
async def test_check_if_token_in_blacklist_returns_false_when_jti_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure denylist callback skips checks when JTI is missing."""
    checker = DummyChecker(return_value=True)

    async def _check_token_revoked_runtime(*, token_type: str, jti: str) -> bool:
        return await checker.is_token_revoked(token_type=token_type, jti=jti)

    monkeypatch.setattr(
        jwt_module,
        "check_token_revoked_runtime",
        _check_token_revoked_runtime,
    )

    callback = cast(
        Callable[[dict[str, str | int | bool]], Awaitable[bool]],
        getattr(cast(Any, AuthJWT), "_token_in_denylist_callback"),
    )
    assert callback is not None
    result = await callback({"type": "access"})

    assert result is False
    assert checker.calls == []


@pytest.mark.asyncio
async def test_check_if_token_in_blacklist_normalizes_token_type_and_uses_checker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure denylist callback normalizes token type before checking."""
    checker = DummyChecker(return_value=True)

    async def _check_token_revoked_runtime(*, token_type: str, jti: str) -> bool:
        return await checker.is_token_revoked(token_type=token_type, jti=jti)

    monkeypatch.setattr(
        jwt_module,
        "check_token_revoked_runtime",
        _check_token_revoked_runtime,
    )

    callback = cast(
        Callable[[dict[str, str | int | bool]], Awaitable[bool]],
        getattr(cast(Any, AuthJWT), "_token_in_denylist_callback"),
    )
    assert callback is not None
    result = await callback({"jti": "abc-123", "type": "  Access "})

    assert result is True
    assert checker.calls == [("access", "abc-123")]
