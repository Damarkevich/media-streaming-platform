from typing import Any

from _pytest.monkeypatch import MonkeyPatch
from typer.testing import CliRunner

import src.cli as cli


class _FakeSessionContext:
    """Minimal async context manager used to stub DB session factory."""

    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


def test_create_superuser_cli_success(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI prints success message when superuser creation succeeds."""

    create_user_payload: dict[str, Any] = {}

    class FakeUserService:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def create_user(self, **kwargs: Any) -> None:
            create_user_payload.update(kwargs)

    monkeypatch.setattr(cli, "async_session", lambda: _FakeSessionContext())
    monkeypatch.setattr(cli, "UserService", FakeUserService)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--login",
            "admin",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 0
    assert "Superuser 'admin' created successfully." in result.stdout
    assert create_user_payload == {
        "login": "admin",
        "password": "StrongPass1!",
        "first_name": "Super",
        "last_name": "Admin",
        "is_superuser": True,
    }


def test_create_superuser_cli_duplicate_login(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI returns code 1 with readable message on duplicate login."""

    class FakeUserService:
        def __init__(self, db: Any) -> None:
            self.db = db

        async def create_user(self, **kwargs: Any) -> None:
            raise cli.UserAlreadyExistsError()

    monkeypatch.setattr(cli, "async_session", lambda: _FakeSessionContext())
    monkeypatch.setattr(cli, "UserService", FakeUserService)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--login",
            "admin",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 1
    assert "User with login 'admin' already exists." in result.output


def test_create_superuser_cli_invalid_login(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI fails before DB call when login format is invalid."""

    is_user_service_initialized = False

    class GuardUserService:
        def __init__(self, db: Any) -> None:
            nonlocal is_user_service_initialized
            is_user_service_initialized = True

    monkeypatch.setattr(cli, "UserService", GuardUserService)
    monkeypatch.setattr(cli, "async_session", lambda: _FakeSessionContext())

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--login",
            "bad_login!",
            "--password",
            "StrongPass1!",
        ],
    )

    assert result.exit_code == 1
    assert "login must be alphanumeric" in result.output
    assert is_user_service_initialized is False


def test_create_superuser_cli_invalid_password(monkeypatch: MonkeyPatch) -> None:
    """Ensure CLI fails before DB call when password is weak."""

    is_user_service_initialized = False

    class GuardUserService:
        def __init__(self, db: Any) -> None:
            nonlocal is_user_service_initialized
            is_user_service_initialized = True

    monkeypatch.setattr(cli, "UserService", GuardUserService)
    monkeypatch.setattr(cli, "async_session", lambda: _FakeSessionContext())

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "create-superuser",
            "--login",
            "admin",
            "--password",
            "weakpass",
        ],
    )

    assert result.exit_code == 1
    assert (
        "password must contain at least one uppercase English letter" in result.output
    )
    assert is_user_service_initialized is False
