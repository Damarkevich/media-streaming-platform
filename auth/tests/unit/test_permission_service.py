from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.services.permissions import (
    PermissionNotFoundError,
    PermissionService,
    RoleNotFoundError,
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
    """Result stub exposing `.scalars()` API."""

    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


class _RowCountResult:
    """Result stub exposing rowcount for DELETE operations."""

    def __init__(self, rowcount: int) -> None:
        self.rowcount = rowcount


def _integrity_error() -> IntegrityError:
    """Create generic SQLAlchemy IntegrityError for branch testing."""
    return IntegrityError("statement", {}, Exception("duplicate"))


@pytest.mark.asyncio
async def test_assign_permission_to_role_raises_when_role_not_found() -> None:
    """Ensure assignment fails with domain error when role does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RoleNotFoundError):
        await service.assign_permission_to_role(uuid4(), uuid4())

    service._permission_exists.assert_not_awaited()  # type: ignore[attr-defined]
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_permission_to_role_raises_when_permission_not_found() -> None:
    """Ensure assignment fails with domain error when permission does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(PermissionNotFoundError):
        await service.assign_permission_to_role(uuid4(), uuid4())

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_assign_permission_to_role_returns_when_relation_exists() -> None:
    """Ensure assignment is idempotent when relation already exists."""
    db = AsyncMock()
    db.add = MagicMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._role_permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await service.assign_permission_to_role(uuid4(), uuid4())

    db.add.assert_not_called()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_permission_to_role_integrity_error_idempotent() -> None:
    """Ensure duplicate race on commit is treated as successful idempotent call."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._role_permission_exists = AsyncMock(side_effect=[False, True])  # type: ignore[method-assign]

    await service.assign_permission_to_role(uuid4(), uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_permission_to_role_integrity_error_reraises_when_not_existing() -> (
    None
):
    """Ensure integrity errors are re-raised when relation still absent after rollback."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=_integrity_error())
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._role_permission_exists = AsyncMock(side_effect=[False, False])  # type: ignore[method-assign]

    with pytest.raises(IntegrityError):
        await service.assign_permission_to_role(uuid4(), uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_permission_from_role_returns_without_commit_when_nothing_deleted() -> (
    None
):
    """Ensure remove operation is no-op when relation is absent."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(0))
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    await service.remove_permission_from_role(uuid4(), uuid4())

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_permission_from_role_commits_and_invalidates_users() -> None:
    """Ensure successful removal commits and invalidates affected users."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_RowCountResult(1))
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._invalidate_role_users_permissions_cache = AsyncMock()  # type: ignore[method-assign]
    role_id = uuid4()

    await service.remove_permission_from_role(role_id, uuid4())

    db.commit.assert_awaited_once()
    service._invalidate_role_users_permissions_cache.assert_awaited_once_with(role_id)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_invalidate_role_users_permissions_cache_calls_invalidator_for_each_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure role-user cache invalidation runs per affected user id."""
    user_ids = [uuid4(), uuid4()]
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(return_value=_ScalarsResult(user_ids))
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    invalidate_mock = AsyncMock()
    monkeypatch.setattr(
        "src.services.permissions.invalidate_user_permissions_cache", invalidate_mock
    )

    await service._invalidate_role_users_permissions_cache(uuid4())

    assert invalidate_mock.await_count == len(user_ids)
    invalidate_mock.assert_any_await(redis_client, user_ids[0])
    invalidate_mock.assert_any_await(redis_client, user_ids[1])


@pytest.mark.asyncio
async def test_get_permissions_returns_scalars_list() -> None:
    """Ensure paginated permissions query returns scalar list payload."""
    db = AsyncMock()
    db.add = MagicMock()
    expected = [MagicMock(name="permission-1"), MagicMock(name="permission-2")]
    db.execute = AsyncMock(return_value=_ScalarsResult(expected))
    service = PermissionService(db=db, redis_client=AsyncMock())

    result = await service.get_permissions(page_size=10, page_number=0)

    assert result == expected
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_permissions_by_role_id_returns_scalars_list() -> None:
    """Ensure role-permissions query returns scalar list payload."""
    db = AsyncMock()
    db.add = MagicMock()
    expected = [MagicMock(name="permission-1")]
    db.execute = AsyncMock(return_value=_ScalarsResult(expected))
    service = PermissionService(db=db, redis_client=AsyncMock())

    result = await service.get_permissions_by_role_id(uuid4())

    assert result == expected


@pytest.mark.asyncio
async def test_role_and_permission_existence_helpers_return_expected_booleans() -> None:
    """Ensure private existence helpers map scalar results to bool values."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=lambda: uuid4()),
            MagicMock(scalar_one_or_none=lambda: None),
        ]
    )
    service = PermissionService(db=db, redis_client=AsyncMock())

    role_exists = await service._role_exists(uuid4())
    permission_exists = await service._permission_exists(uuid4())

    assert role_exists is True
    assert permission_exists is False


@pytest.mark.asyncio
async def test_role_permission_exists_helper_returns_boolean() -> None:
    """Ensure relation helper returns True only when relation row exists."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(
        side_effect=[_ScalarsResult([MagicMock()]), _ScalarsResult([])]
    )
    service = PermissionService(db=db, redis_client=AsyncMock())

    first = await service._role_permission_exists(uuid4(), uuid4())
    second = await service._role_permission_exists(uuid4(), uuid4())

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_assign_permission_to_role_success_commits_and_invalidates() -> None:
    """Ensure successful permission assignment commits and invalidates role users."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._role_permission_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service._invalidate_role_users_permissions_cache = AsyncMock()  # type: ignore[method-assign]
    role_id = uuid4()

    await service.assign_permission_to_role(role_id, uuid4())

    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    service._invalidate_role_users_permissions_cache.assert_awaited_once_with(role_id)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_assign_permission_to_role_reraises_sqlalchemy_error() -> None:
    """Ensure generic SQLAlchemy errors in assignment are rolled back and re-raised."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    redis_client = AsyncMock()
    service = PermissionService(db=db, redis_client=redis_client)
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._role_permission_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(SQLAlchemyError):
        await service.assign_permission_to_role(uuid4(), uuid4())

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_permission_from_role_raises_when_role_missing() -> None:
    """Ensure remove operation fails with domain error when role does not exist."""
    db = AsyncMock()
    db.add = MagicMock()
    service = PermissionService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock()  # type: ignore[method-assign]

    with pytest.raises(RoleNotFoundError):
        await service.remove_permission_from_role(uuid4(), uuid4())

    service._permission_exists.assert_not_awaited()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_remove_permission_from_role_raises_when_permission_missing() -> None:
    """Ensure remove operation fails with domain error when permission is absent."""
    db = AsyncMock()
    db.add = MagicMock()
    service = PermissionService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=False)  # type: ignore[method-assign]

    with pytest.raises(PermissionNotFoundError):
        await service.remove_permission_from_role(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_remove_permission_from_role_reraises_sqlalchemy_error() -> None:
    """Ensure SQLAlchemy errors in remove operation are rolled back and re-raised."""
    db = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock(side_effect=SQLAlchemyError("db failed"))
    db.rollback = AsyncMock()
    service = PermissionService(db=db, redis_client=AsyncMock())
    service._role_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._permission_exists = AsyncMock(return_value=True)  # type: ignore[method-assign]

    with pytest.raises(SQLAlchemyError):
        await service.remove_permission_from_role(uuid4(), uuid4())

    db.rollback.assert_awaited_once()
