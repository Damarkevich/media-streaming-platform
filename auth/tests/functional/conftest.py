from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from types import SimpleNamespace
from typing import Any, AsyncGenerator
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.core.jwt import auth_dep
from src.core.limiter import limiter
from src.main import app
from src.models.log import LogType
from src.schemas.users import UserResponse
from src.services.roles import get_role_service
from src.services.tokens import get_token_service
from src.services.users import UserAlreadyExistsError, get_user_service


@pytest_asyncio.fixture(autouse=True)
async def clear_dependency_overrides() -> AsyncGenerator[None, None]:
    """Reset dependency overrides after each functional test."""
    limiter.reset()
    yield
    limiter.reset()
    app.dependency_overrides.clear()


@dataclass
class FakeLogEntry:
    """In-memory audit log entry used by fake services in tests."""

    log_type: LogType
    created_at: datetime


def _default_log_entries() -> list[FakeLogEntry]:
    """Return default empty log list for dataclass field factory."""
    return []


@dataclass
class FakeUserService:
    """Fake user service implementation used by functional tests."""

    created_user_id: UUID = field(default_factory=uuid4)
    authenticated_user_id: UUID = field(default_factory=uuid4)
    existing_user: UserResponse | None = field(
        default_factory=lambda: UserResponse(
            id=uuid4(),
            email="ivan@example.com",
            first_name="Ivan",
            last_name="Ivanov",
            roles=[],
        )
    )
    changed_email: str | None = None
    changed_password: str | None = None
    last_logged_user_id: str | None = None
    last_logged_type: LogType | None = None
    user_logs: list[FakeLogEntry] = field(default_factory=_default_log_entries)

    def __post_init__(self) -> None:
        if not self.user_logs:
            self.user_logs = [
                FakeLogEntry(
                    log_type=LogType.LOGIN,
                    created_at=datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc),
                ),
                FakeLogEntry(
                    log_type=LogType.LOGIN,
                    created_at=datetime(2026, 3, 1, 11, 0, 0, tzinfo=timezone.utc),
                ),
            ]

    async def create_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> UserResponse:
        if email == "duplicate@example.com":
            raise UserAlreadyExistsError()
        return UserResponse(
            id=self.created_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            roles=[],
        )

    async def authenticate_user(
        self, email: str, password: str
    ) -> SimpleNamespace | None:
        if email == "bad@example.com" or password == "bad":
            return None
        return SimpleNamespace(id=self.authenticated_user_id)

    async def log_user_action(self, user: Any, log_type: LogType) -> None:
        self.last_logged_user_id = str(user.id)
        self.last_logged_type = log_type

    async def get_user_by_id(self, user_id: UUID) -> UserResponse | None:
        if self.existing_user and self.existing_user.id == user_id:
            return self.existing_user
        return None

    async def change_email(self, user_id: UUID, new_email: str) -> bool:
        if not self.existing_user or self.existing_user.id != user_id:
            return False
        if new_email == "duplicate@example.com":
            raise UserAlreadyExistsError()
        self.changed_email = new_email
        return True

    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        if not self.existing_user or self.existing_user.id != user_id:
            return False
        self.changed_password = new_password
        return True

    async def get_user_logs(
        self, user_id: UUID, page_size: int, page_number: int
    ) -> list[FakeLogEntry]:
        if not self.existing_user or self.existing_user.id != user_id:
            return []
        offset = page_number * page_size
        return self.user_logs[offset : offset + page_size]


@dataclass
class FakeTokenService:
    """Fake token service used by functional tests."""

    last_access_blacklisted_jti: str | None = None
    last_refresh_blacklisted_jti: str | None = None

    async def issue_tokens(
        self,
        user_id: UUID,
        roles_names: list[str] | None = None,
        fresh: bool = False,
    ) -> tuple[str, str]:
        return (f"access-{user_id}", f"refresh-{user_id}")

    async def add_access_to_blacklist(self, jti: str) -> None:
        self.last_access_blacklisted_jti = jti

    async def add_refresh_to_blacklist(self, jti: str) -> None:
        self.last_refresh_blacklisted_jti = jti


class FakeAuth:
    """Fake AuthJWT adapter for authenticated test scenarios."""

    def __init__(
        self,
        *,
        subject: str,
        jti: str = "refresh-jti",
        is_fresh: bool = True,
        is_authorized: bool = True,
    ) -> None:
        self.subject = subject
        self.jti = jti
        self.is_fresh = is_fresh
        self.is_authorized = is_authorized

    async def jwt_required(self) -> None:
        if not self.is_authorized:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Authentication required",
            )
        return None

    async def jwt_refresh_token_required(self) -> None:
        return None

    async def fresh_jwt_required(self) -> None:
        if not self.is_fresh:
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail="Fresh token required",
            )

    async def get_jwt_subject(self) -> str:
        return self.subject

    async def get_raw_jwt(self) -> dict[str, str]:
        return {"jti": self.jti}


class FakeRoleService:
    """Fake role service used by functional tests."""

    async def get_roles_by_user_id(self, user_id: UUID) -> list[object]:
        return []


@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Build ASGI test client with default fake dependencies."""
    fake_user_service = FakeUserService()
    fake_token_service = FakeTokenService()
    existing_user = fake_user_service.existing_user
    assert existing_user is not None
    fake_auth = FakeAuth(subject=str(existing_user.id))

    app.dependency_overrides[get_user_service] = lambda: fake_user_service
    app.dependency_overrides[get_token_service] = lambda: fake_token_service
    app.dependency_overrides[get_role_service] = lambda: FakeRoleService()
    app.dependency_overrides[auth_dep] = lambda: fake_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.fake_user_service = fake_user_service  # type: ignore[attr-defined]
        client.fake_token_service = fake_token_service  # type: ignore[attr-defined]
        client.fake_auth = fake_auth  # type: ignore[attr-defined]
        yield client
