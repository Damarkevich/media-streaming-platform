import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.db.postgres import async_session, engine
from src.main import app
from src.services.roles import get_role_service
from src.services.tokens import get_token_service

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(autouse=True)
async def reset_db_pool() -> AsyncGenerator[None, None]:
    """Avoid cross-test asyncpg loop/pool conflicts by resetting pool."""
    await engine.dispose()
    yield
    await engine.dispose()


class FakeTokenService:
    """Fake token issuer for login logging integration tests."""

    async def issue_tokens(
        self,
        user_id: uuid.UUID,
        roles_names: list[str] | None = None,
        fresh: bool = False,
    ) -> tuple[str, str]:
        return (f"access-{user_id}", f"refresh-{user_id}")


class FakeRoleService:
    """Fake role provider for login integration tests."""

    async def get_roles_by_user_id(self, user_id: uuid.UUID) -> list[object]:
        return []


def _override_token_service() -> None:
    """Override token and role service dependencies with fakes."""
    app.dependency_overrides[get_token_service] = lambda: FakeTokenService()
    app.dependency_overrides[get_role_service] = lambda: FakeRoleService()


def _build_test_client() -> AsyncClient:
    """Create ASGI test client bound to the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _signup_user(client: AsyncClient, login: str, password: str) -> str:
    """Create test user and return created user identifier."""
    signup_response = await client.post(
        "/api/v1/auth/signup",
        json={
            "login": login,
            "password": password,
            "first_name": "Log",
            "last_name": "Check",
        },
    )
    assert signup_response.status_code == 201
    return signup_response.json()["id"]


async def _count_login_logs(user_id: str) -> int:
    """Count login audit records for the given user."""
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM auth.logs WHERE user_id = :uid AND log_type = 'login'"
            ),
            {"uid": user_id},
        )
        return int(result.scalar_one())


async def _latest_log_type(user_id: str) -> str | None:
    """Return latest log type for the given user."""
    async with async_session() as session:
        result = await session.execute(
            text(
                "SELECT log_type FROM auth.logs WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"
            ),
            {"uid": user_id},
        )
        return result.scalar_one_or_none()


async def _cleanup_user_data(user_id: str) -> None:
    """Remove user and related logs created during tests."""
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM auth.logs WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await session.execute(
            text("DELETE FROM auth.users WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()


async def test_login_writes_audit_log_to_db() -> None:
    """Ensure successful login persists one login audit record."""
    login = f"logcheck{uuid.uuid4().hex[:10]}"
    password = "StrongPass1!"

    _override_token_service()
    user_id: str | None = None

    try:
        async with _build_test_client() as client:
            user_id = await _signup_user(client, login, password)
            before_count = await _count_login_logs(user_id)

            login_response = await client.post(
                "/api/v1/auth/login",
                json={"login": login, "password": password},
            )
            assert login_response.status_code == 200

            after_count = await _count_login_logs(user_id)
            latest_log_type = await _latest_log_type(user_id)

            assert after_count == before_count + 1
            assert latest_log_type == "login"
    finally:
        app.dependency_overrides.clear()

        if user_id is not None:
            await _cleanup_user_data(user_id)


async def test_login_with_invalid_password_does_not_write_audit_log() -> None:
    """Ensure failed login does not create login audit record."""
    login = f"logcheck{uuid.uuid4().hex[:10]}"
    password = "StrongPass1!"

    _override_token_service()
    user_id: str | None = None

    try:
        async with _build_test_client() as client:
            user_id = await _signup_user(client, login, password)
            before_count = await _count_login_logs(user_id)

            login_response = await client.post(
                "/api/v1/auth/login",
                json={"login": login, "password": "WrongPass1!"},
            )
            assert login_response.status_code == 401

            after_count = await _count_login_logs(user_id)

            assert after_count == before_count
    finally:
        app.dependency_overrides.clear()

        if user_id is not None:
            await _cleanup_user_data(user_id)
