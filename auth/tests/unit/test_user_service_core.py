from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.user import User
from src.services.users import UserAlreadyExistsError, UserService


class _Scalars:
    """Scalars wrapper stub for SQLAlchemy result compatibility."""

    def __init__(self, value) -> None:
        self._value = value

    def one_or_none(self):
        return self._value

    def all(self):
        return self._value


class _Result:
    """Result stub exposing `.scalars()` API."""

    def __init__(self, value) -> None:
        self._value = value

    def scalars(self):
        return _Scalars(self._value)


def _integrity_error() -> IntegrityError:
    """Create generic SQLAlchemy IntegrityError for branch testing."""
    return IntegrityError("statement", {}, Exception("duplicate"))


@pytest.mark.asyncio
async def test_create_user_success_refreshes_and_returns_user() -> None:
    """Ensure successful user creation commits and refreshes ORM entity."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    service = UserService(db=db)

    created = await service.create_user(
        email="new_user@example.com",
        password="StrongPass1!",
        first_name="Ivan",
        last_name="Ivanov",
    )

    assert isinstance(created, User)
    assert created.email == "new_user@example.com"
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_change_password_returns_true_when_user_found() -> None:
    """Ensure password change returns True when update matches a user row."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(MagicMock()))
    db.commit = AsyncMock()
    service = UserService(db=db)

    result = await service.change_password(uuid4(), "NewStrongPass1!")

    assert result is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_returns_false_when_user_missing() -> None:
    """Ensure password change returns False when no user row is updated."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(None))
    db.commit = AsyncMock()
    service = UserService(db=db)

    result = await service.change_password(uuid4(), "NewStrongPass1!")

    assert result is False


@pytest.mark.asyncio
async def test_change_email_returns_false_when_user_missing() -> None:
    """Ensure email change returns False when no user row is updated."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(None))
    db.commit = AsyncMock()
    service = UserService(db=db)

    result = await service.change_email(uuid4(), "new_login@example.com")

    assert result is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_email_maps_unique_violation_to_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure duplicate email change maps DB integrity error to domain error."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = UserService(db=db)
    monkeypatch.setattr(
        "src.services.users.is_field_unique_violation", lambda *args: True
    )

    with pytest.raises(UserAlreadyExistsError):
        await service.change_email(uuid4(), "duplicate@example.com")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_email_uses_normalized_value_in_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure change_email writes normalized email returned by model helper."""
    captured_stmt = None

    async def _capture_execute(stmt):
        nonlocal captured_stmt
        captured_stmt = stmt
        return _Result(MagicMock())

    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=_capture_execute)
    db.commit = AsyncMock()
    service = UserService(db=db)

    monkeypatch.setattr(
        User, "normalize_email", classmethod(lambda cls, v: "normalized@example.com")
    )

    result = await service.change_email(uuid4(), "  MIXED@Example.COM  ")

    assert result is True
    assert captured_stmt is not None
    params = captured_stmt.compile().params
    assert "normalized@example.com" in params.values()


@pytest.mark.asyncio
async def test_authenticate_user_returns_none_for_wrong_password() -> None:
    """Ensure authentication fails for invalid password."""
    password_hash = await User.hash_password("StrongPass1!")
    user = User(
        email="auth_user@example.com",
        password_hash=password_hash,
        first_name="Ivan",
        last_name="Ivanov",
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(user))
    service = UserService(db=db)

    result = await service.authenticate_user("auth_user@example.com", "WrongPass1!")

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_id_returns_none_when_missing() -> None:
    """Ensure user lookup returns None when user does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(None))
    service = UserService(db=db)

    result = await service.get_user_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_user_logs_returns_scalar_list_payload() -> None:
    """Ensure user logs query returns list from scalar rows."""
    logs = [MagicMock(name="log-1"), MagicMock(name="log-2")]
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_Result(logs))
    service = UserService(db=db)

    result = await service.get_user_logs(uuid4(), page_size=10, page_number=0)

    assert result == logs


@pytest.mark.asyncio
async def test_create_user_reraises_non_unique_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure create_user re-raises integrity errors unrelated to email uniqueness."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = UserService(db=db)
    monkeypatch.setattr(
        "src.services.users.is_field_unique_violation", lambda *args: False
    )

    with pytest.raises(IntegrityError):
        await service.create_user(
            email="duplicate_user@example.com",
            password="StrongPass1!",
            first_name="Ivan",
            last_name="Ivanov",
        )

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_email_reraises_non_unique_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure change_email re-raises integrity errors not tied to email uniqueness."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = UserService(db=db)
    monkeypatch.setattr(
        "src.services.users.is_field_unique_violation", lambda *args: False
    )

    with pytest.raises(IntegrityError):
        await service.change_email(uuid4(), "duplicate@example.com")

    db.rollback.assert_awaited_once()
