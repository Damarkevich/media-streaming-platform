from dataclasses import dataclass, field
from http import HTTPStatus
from types import SimpleNamespace
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.core.jwt import auth_dep
from src.main import app
from src.models.log import LogType
from src.schemas.users import UserResponse
from src.services.tokens import get_token_service
from src.services.users import UserAlreadyExistsError, get_user_service


@dataclass
class FakeUserService:
    created_user_id: UUID = field(default_factory=uuid4)
    authenticated_user_id: UUID = field(default_factory=uuid4)
    existing_user: UserResponse | None = field(
        default_factory=lambda: UserResponse(
            id=uuid4(), first_name="Ivan", last_name="Ivanov"
        )
    )
    changed_login: str | None = None
    changed_password: str | None = None
    last_logged_user_id: str | None = None
    last_logged_type: LogType | None = None

    async def create_user(
        self,
        login: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> UserResponse:
        if login == "duplicate":
            raise UserAlreadyExistsError()
        return UserResponse(
            id=self.created_user_id,
            first_name=first_name,
            last_name=last_name,
        )

    async def authenticate_user(self, login: str, password: str):
        if login == "bad" or password == "bad":
            return None
        return SimpleNamespace(id=self.authenticated_user_id)

    async def log_user_action(self, user, log_type) -> None:
        self.last_logged_user_id = str(user.id)
        self.last_logged_type = log_type

    async def get_user_by_id(self, user_id: str) -> UserResponse | None:
        if self.existing_user and str(self.existing_user.id) == user_id:
            return self.existing_user
        return None

    async def change_login(self, user_id: str, new_login: str) -> bool:
        if not self.existing_user or str(self.existing_user.id) != user_id:
            return False
        if new_login == "duplicate":
            raise UserAlreadyExistsError()
        self.changed_login = new_login
        return True

    async def change_password(self, user_id: str, new_password: str) -> bool:
        if not self.existing_user or str(self.existing_user.id) != user_id:
            return False
        self.changed_password = new_password
        return True


@dataclass
class FakeTokenService:
    last_access_blacklisted_jti: str | None = None
    last_refresh_blacklisted_jti: str | None = None

    async def issue_tokens(self, user_id: str, fresh: bool = False) -> tuple[str, str]:
        return (f"access-{user_id}", f"refresh-{user_id}")

    async def add_access_to_blacklist(self, jti: str) -> None:
        self.last_access_blacklisted_jti = jti

    async def add_refresh_to_blacklist(self, jti: str) -> None:
        self.last_refresh_blacklisted_jti = jti


class FakeAuth:
    def __init__(
        self,
        *,
        subject: str,
        jti: str = "refresh-jti",
        is_fresh: bool = True,
    ) -> None:
        self.subject = subject
        self.jti = jti
        self.is_fresh = is_fresh

    async def jwt_required(self) -> None:
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


@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    fake_user_service = FakeUserService()
    fake_token_service = FakeTokenService()
    existing_user = fake_user_service.existing_user
    assert existing_user is not None
    fake_auth = FakeAuth(subject=str(existing_user.id))

    app.dependency_overrides[get_user_service] = lambda: fake_user_service
    app.dependency_overrides[get_token_service] = lambda: fake_token_service
    app.dependency_overrides[auth_dep] = lambda: fake_auth

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.fake_user_service = fake_user_service  # type: ignore[attr-defined]
        client.fake_token_service = fake_token_service  # type: ignore[attr-defined]
        client.fake_auth = fake_auth  # type: ignore[attr-defined]
        yield client

    app.dependency_overrides.clear()
