from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.db import redis as redis_module
from src.db.postgres import get_session
from src.main import app
from src.services.roles import get_role_service
from src.services.users import get_user_service


class FakeUserServiceForLogin:
    """Minimal user service for login flow in denylist tests."""

    async def authenticate_user(
        self, email: str, password: str
    ) -> SimpleNamespace | None:
        if email == "valid_user@example.com" and password == "ValidPass1!":
            return SimpleNamespace(id="8d2f1ca5-f48a-4eb3-a56e-5a6d5a5c0d42")
        return None

    async def log_user_action(self, user: Any, log_type: Any) -> None:
        return None


class FakeRoleServiceForLogin:
    """Role service stub for login flow in denylist tests."""

    async def get_roles_by_user_id(self, user_id: Any) -> list[Any]:
        return []


class _FakeScalarResult:
    """Scalar result stub compatible with SQLAlchemy result API."""

    def __init__(self, value: object | None) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object | None:
        return self.value


class InMemoryBlacklistSession:
    """In-memory session emulating refresh-token blacklist behavior."""

    def __init__(self, storage: set[str]) -> None:
        self.storage = storage

    def add(self, token: Any) -> None:
        self.storage.add(str(token.jti))

    async def commit(self) -> None:
        return None

    async def refresh(self, token: Any) -> None:
        return None

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        params = stmt.compile().params
        jti = str(next(iter(params.values()), ""))
        if jti and "jti" in params and jti not in self.storage:
            self.storage.add(jti)
            return _FakeScalarResult(None)
        if jti in self.storage:
            return _FakeScalarResult(object())
        return _FakeScalarResult(None)


class FakeRedis:
    """Minimal in-memory Redis stub used by denylist tests."""

    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def setex(self, name: str, time: int, value: str) -> None:
        self.storage[name] = value


async def _build_auth_client(
    monkeypatch: pytest.MonkeyPatch,
    blacklisted_jtis: set[str],
) -> AsyncClient:
    """Build test client with overridden auth dependencies and in-memory stores."""
    redis_module.redis = FakeRedis()

    async def override_get_session() -> AsyncGenerator[InMemoryBlacklistSession, None]:
        yield InMemoryBlacklistSession(blacklisted_jtis)

    @asynccontextmanager
    async def fake_async_session_ctx() -> AsyncGenerator[
        InMemoryBlacklistSession, None
    ]:
        yield InMemoryBlacklistSession(blacklisted_jtis)

    monkeypatch.setattr(
        "src.services.blacklist.async_session",
        lambda: fake_async_session_ctx(),
    )

    app.dependency_overrides[get_user_service] = lambda: FakeUserServiceForLogin()
    app.dependency_overrides[get_role_service] = lambda: FakeRoleServiceForLogin()
    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@asynccontextmanager
async def _auth_client_ctx(
    monkeypatch: pytest.MonkeyPatch,
    blacklisted_jtis: set[str],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide managed test client context for denylist scenarios."""
    client = await _build_auth_client(monkeypatch, blacklisted_jtis)
    try:
        async with client as open_client:
            yield open_client
    finally:
        app.dependency_overrides.clear()


async def _login_and_get_tokens(client: AsyncClient) -> tuple[str, str]:
    """Authenticate test user and return issued access/refresh tokens."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "valid_user@example.com", "password": "ValidPass1!"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    return body["access_token"], body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_token_is_revoked_after_logout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure refresh token becomes unusable after refresh revoke call."""
    blacklisted_jtis: set[str] = set()

    async with _auth_client_ctx(monkeypatch, blacklisted_jtis) as client:
        _, refresh_token = await _login_and_get_tokens(client)

        logout_response = await client.delete(
            "/api/v1/auth/refresh-revoke",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert logout_response.status_code == 204

        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert refresh_response.status_code == 401
        assert refresh_response.json()["detail"] == "Token has been revoked"

        refresh_response_again = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert refresh_response_again.status_code == 401
        assert refresh_response_again.json()["detail"] == "Token has been revoked"


@pytest.mark.asyncio
async def test_access_token_is_revoked_after_access_revoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure access token is rejected after access revoke call."""
    blacklisted_jtis: set[str] = set()

    async with _auth_client_ctx(monkeypatch, blacklisted_jtis) as client:
        access_token, _ = await _login_and_get_tokens(client)

        first_revoke = await client.delete(
            "/api/v1/auth/access-revoke",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert first_revoke.status_code == 204

        second_revoke = await client.delete(
            "/api/v1/auth/access-revoke",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert second_revoke.status_code == 401
        assert second_revoke.json()["detail"] == "Token has been revoked"


@pytest.mark.asyncio
async def test_refresh_with_access_token_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure refresh endpoint rejects access tokens."""
    blacklisted_jtis: set[str] = set()

    async with _auth_client_ctx(monkeypatch, blacklisted_jtis) as client:
        access_token, _ = await _login_and_get_tokens(client)

        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 422
        assert isinstance(response.json().get("detail"), str)


@pytest.mark.asyncio
async def test_me_with_refresh_token_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure access-protected endpoint rejects refresh tokens."""
    blacklisted_jtis: set[str] = set()

    async with _auth_client_ctx(monkeypatch, blacklisted_jtis) as client:
        _, refresh_token = await _login_and_get_tokens(client)

        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 422
        assert isinstance(response.json().get("detail"), str)


@pytest.mark.asyncio
async def test_refresh_with_expired_refresh_token_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure expired refresh token cannot be used to rotate tokens."""
    blacklisted_jtis: set[str] = set()
    monkeypatch.setattr("src.services.tokens.settings.refresh_token_expires", -1)

    async with _auth_client_ctx(monkeypatch, blacklisted_jtis) as client:
        _, refresh_token = await _login_and_get_tokens(client)

        response = await client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 422
        assert isinstance(response.json().get("detail"), str)
