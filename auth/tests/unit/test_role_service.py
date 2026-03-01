from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.services.roles import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    RoleService,
    UserNotFoundError,
)


class _Scalars:
    """Simple scalars-like wrapper for SQLAlchemy result stubs."""

    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ScalarsResult:
    """Result stub exposing `.scalars()` API for `.all()` reads."""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


class _RowCountResult:
    """Result stub exposing rowcount for update/delete operations."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


def _integrity_error() -> IntegrityError:
    """Create generic SQLAlchemy IntegrityError for branch testing."""
    return IntegrityError("statement", {}, Exception("duplicate"))


@pytest.mark.asyncio
async def test_create_role_maps_unique_violation_to_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure duplicate role name is converted to RoleAlreadyExistsError."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    monkeypatch.setattr(
        "src.services.roles.is_field_unique_violation", lambda *args: True
    )

    with pytest.raises(RoleAlreadyExistsError):
        await service.create_role("admin")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_role_returns_false_when_not_found() -> None:
    """Ensure update returns False when target role is absent."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(0))
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)

    is_updated = await service.update_role(uuid4(), "new-name")

    assert is_updated is False
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_role_to_user_raises_when_role_missing() -> None:
    """Ensure role assignment fails when role does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service._user_exists = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RoleNotFoundError):
        await service.assign_role_to_user(uuid4(), uuid4())

    service._user_exists.assert_not_awaited()  # type: ignore[attr-defined]
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_role_to_user_raises_when_user_missing() -> None:
    """Ensure role assignment fails when user does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(UserNotFoundError):
        await service.assign_role_to_user(uuid4(), uuid4())

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_role_to_user_returns_when_relation_exists() -> None:
    """Ensure role assignment is idempotent when relation already exists."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await service.assign_role_to_user(uuid4(), uuid4())

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_role_to_user_integrity_error_idempotent() -> None:
    """Ensure duplicate race on assign commit is treated as idempotent success."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_role_exists = AsyncMock(side_effect=[False, True])  # type: ignore[method-assign]

    await service.assign_role_to_user(uuid4(), uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_role_returns_false_when_missing() -> None:
    """Ensure role delete returns False when role row is absent."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarsResult([]), _RowCountResult(0)])
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)

    is_deleted = await service.delete_role(uuid4())

    assert is_deleted is False
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_role_invalidates_permissions_cache_for_affected_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure deleting role invalidates cache for all users assigned to it."""
    user_ids = [uuid4(), uuid4()]
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=[_ScalarsResult(user_ids), _RowCountResult(1)])
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.services.roles.invalidate_user_permissions_cache", invalidate_mock
    )

    is_deleted = await service.delete_role(uuid4())

    assert is_deleted is True
    db.commit.assert_awaited_once()
    assert invalidate_mock.await_count == len(user_ids)
    invalidate_mock.assert_any_await(redis_client, user_ids[0])
    invalidate_mock.assert_any_await(redis_client, user_ids[1])
