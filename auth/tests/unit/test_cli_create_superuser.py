from typing import Any
from uuid import uuid4

from _pytest.monkeypatch import MonkeyPatch
from typer.testing import CliRunner

import src.cli as cli


class _FakeSessionContext:
    """Minimal async context manager used to stub DB session factory."""

    def __init__(self, db: Any) -> None:
        self._db = db

    async def __aenter__(self) -> Any:
        return self._db

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _FakeExecuteResult:
    def __init__(self, role: Any) -> None:
        self._role = role

    def scalars(self) -> "_FakeExecuteResult":
        return self

    def one_or_none(self) -> Any:
        return self._role


class _FakeSession:
    def __init__(self, role: Any) -> None:
        self._role = role

    async def execute(self, _stmt: Any) -> _FakeExecuteResult:
        return _FakeExecuteResult(self._role)

    def add(self, _obj: Any) -> None:
        return None

    async def commit(self) -> None:
        return None


def test_create_superuser_cli_success(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI prints success message when superuser creation succeeds."""

    create_user_payload: dict[str, Any] = {}

    class FakeUserService:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def create_user(self, **kwargs: Any) -> Any:
            create_user_payload.update(kwargs)
            return type("FakeUser", (), {"id": uuid4()})()

    fake_role = type("FakeRole", (), {"id": uuid4()})()
    monkeypatch.setattr(
        cli,
        "async_session",
        lambda: _FakeSessionContext(_FakeSession(role=fake_role)),
    )
    monkeypatch.setattr(cli, "UserService", FakeUserService)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--email",
            "admin@example.com",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 0
    assert "Superuser 'admin@example.com' created successfully." in result.stdout
    assert create_user_payload == {
        "email": "admin@example.com",
        "password": "StrongPass1!",
        "first_name": "Super",
        "last_name": "Admin",
        "is_superuser": True,
    }


def test_create_superuser_cli_duplicate_email(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI returns code 1 with readable message on duplicate email."""

    class FakeUserService:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def create_user(self, **kwargs: Any) -> None:
            raise cli.UserAlreadyExistsError()

    fake_role = type("FakeRole", (), {"id": uuid4()})()
    monkeypatch.setattr(
        cli,
        "async_session",
        lambda: _FakeSessionContext(_FakeSession(role=fake_role)),
    )
    monkeypatch.setattr(cli, "UserService", FakeUserService)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--email",
            "admin@example.com",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 1
    assert "User with email 'admin@example.com' already exists." in result.output


def test_create_superuser_cli_invalid_email(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI fails before DB call when email format is invalid."""

    is_user_service_initialized = False

    class GuardUserService:
        def __init__(self, db: Any) -> None:
            nonlocal is_user_service_initialized
            is_user_service_initialized = True

    monkeypatch.setattr(cli, "UserService", GuardUserService)
    fake_role = type("FakeRole", (), {"id": uuid4()})()
    monkeypatch.setattr(
        cli,
        "async_session",
        lambda: _FakeSessionContext(_FakeSession(role=fake_role)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--email",
            "bad_email",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid email format" in result.output
    assert is_user_service_initialized is False


def test_create_superuser_cli_invalid_password(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI fails before DB call when password is weak."""

    is_user_service_initialized = False

    class GuardUserService:
        def __init__(self, db: Any) -> None:
            nonlocal is_user_service_initialized
            is_user_service_initialized = True

    monkeypatch.setattr(cli, "UserService", GuardUserService)
    fake_role = type("FakeRole", (), {"id": uuid4()})()
    monkeypatch.setattr(
        cli,
        "async_session",
        lambda: _FakeSessionContext(_FakeSession(role=fake_role)),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--email",
            "admin@example.com",
            "--password",
            "weakpass",
        ],
    )

    assert result.exit_code == 1
    assert (
        "password must contain at least one uppercase English letter" in result.output
    )
    assert is_user_service_initialized is False
