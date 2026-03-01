from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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

    def one_or_none(self):
        return self._values[0] if self._values else None


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
async def test_assign_role_to_user_integrity_error_reraises_when_relation_absent() -> (
    None
):
    """Ensure IntegrityError is re-raised when relation still absent after rollback."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_role_exists = AsyncMock(side_effect=[False, False])  # type: ignore[method-assign]

    with pytest.raises(IntegrityError):
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


@pytest.mark.asyncio
async def test_update_role_maps_unique_violation_to_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure duplicate role-name update maps to RoleAlreadyExistsError."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    monkeypatch.setattr(
        "src.services.roles.is_field_unique_violation", lambda *args: True
    )

    with pytest.raises(RoleAlreadyExistsError):
        await service.update_role(uuid4(), "admin")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_role_from_user_raises_when_role_missing() -> None:
    """Ensure role removal fails fast when role is missing."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service._user_exists = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RoleNotFoundError):
        await service.remove_role_from_user(uuid4(), uuid4())

    service._user_exists.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_remove_role_from_user_raises_when_user_missing() -> None:
    """Ensure role removal fails when user does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(UserNotFoundError):
        await service.remove_role_from_user(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_remove_role_from_user_noop_when_relation_absent() -> None:
    """Ensure role removal is no-op when user-role relation is absent."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(0))
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await service.remove_role_from_user(uuid4(), uuid4())

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_role_reraises_non_unique_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure create_role re-raises integrity errors unrelated to name uniqueness."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())
    monkeypatch.setattr(
        "src.services.roles.is_field_unique_violation", lambda *args: False
    )

    with pytest.raises(IntegrityError):
        await service.create_role("admin")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_role_reraises_sqlalchemy_error() -> None:
    """Ensure create_role rolls back and re-raises generic SQLAlchemy errors."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())

    with pytest.raises(SQLAlchemyError):
        await service.create_role("admin")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_role_returns_true_when_row_updated() -> None:
    """Ensure update returns True and commits when target row exists."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(1))
    db.commit = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())

    updated = await service.update_role(uuid4(), "updated")

    assert updated is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_role_reraises_non_unique_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure update re-raises integrity errors not related to name uniqueness."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())
    monkeypatch.setattr(
        "src.services.roles.is_field_unique_violation", lambda *args: False
    )

    with pytest.raises(IntegrityError):
        await service.update_role(uuid4(), "updated")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_role_reraises_sqlalchemy_error() -> None:
    """Ensure update rolls back and re-raises generic SQLAlchemy errors."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())

    with pytest.raises(SQLAlchemyError):
        await service.update_role(uuid4(), "updated")

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_role_by_id_returns_scalar_value() -> None:
    """Ensure get_role_by_id returns scalar ORM row from query result."""
    role = MagicMock(name="role")
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarsResult([role]))
    service = RoleService(db=db, redis_client=AsyncMock())

    result = await service.get_role_by_id(uuid4())

    assert result is role


@pytest.mark.asyncio
async def test_get_roles_by_user_id_returns_scalars_list() -> None:
    """Ensure get_roles_by_user_id returns scalar role list."""
    roles = [MagicMock(name="role-1"), MagicMock(name="role-2")]
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarsResult(roles))
    service = RoleService(db=db, redis_client=AsyncMock())

    result = await service.get_roles_by_user_id(uuid4())

    assert result == roles


@pytest.mark.asyncio
async def test_assign_role_to_user_reraises_sqlalchemy_error() -> None:
    """Ensure assign_role_to_user rolls back and re-raises SQLAlchemy errors."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_role_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(SQLAlchemyError):
        await service.assign_role_to_user(uuid4(), uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_role_from_user_success_commits_and_invalidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure successful role removal commits and invalidates user cache."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(1))
    db.commit = AsyncMock()
    redis_client = AsyncMock()
    service = RoleService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.services.roles.invalidate_user_permissions_cache", invalidate_mock
    )
    user_id = uuid4()

    await service.remove_role_from_user(user_id, uuid4())

    db.commit.assert_awaited_once()
    invalidate_mock.assert_awaited_once_with(redis_client, user_id)


@pytest.mark.asyncio
async def test_remove_role_from_user_reraises_sqlalchemy_error() -> None:
    """Ensure remove_role_from_user rolls back and re-raises SQLAlchemy errors."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    service = RoleService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._user_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(SQLAlchemyError):
        await service.remove_role_from_user(uuid4(), uuid4())

    db.rollback.assert_awaited_once()
