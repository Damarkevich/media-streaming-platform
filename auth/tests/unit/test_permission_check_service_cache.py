from collections.abc import Sequence
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.models.role import PermissionName
from src.services.permission_check import (
    PermissionCheckService,
    invalidate_user_permissions_cache,
)


class _DummyScalars:
    def __init__(self, values: Sequence[PermissionName]) -> None:
        self._values = values

    def all(self):
        return self._values


class _DummyResult:
    def __init__(self, values: Sequence[PermissionName]) -> None:
        self._values = values

    def scalars(self):
        return _DummyScalars(self._values)


class _DummyScalarResult:
    def __init__(self, value: bool | None) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("db_value", "expected"),
    [
        (True, True),
        (False, False),
        (None, False),
    ],
)
async def test_is_superuser_returns_expected_value(
    db_value: bool | None,
    expected: bool,
) -> None:
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_DummyScalarResult(db_value))
    redis_client = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)

    assert await service._is_superuser(user_id) is expected
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_permissions_returns_cached_value_without_db() -> None:
    user_id = uuid4()
    db = AsyncMock()
    redis_client = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)

    redis_client.get_cached_user_permissions = AsyncMock(
        return_value={
            PermissionName.ROLES_READ.value,
            PermissionName.ROLES_UPDATE.value,
        }
    )
    redis_client.set_cached_user_permissions = AsyncMock()

    permissions = await service.get_user_permissions(user_id)

    assert permissions == {PermissionName.ROLES_READ, PermissionName.ROLES_UPDATE}
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_user_permissions_queries_db_and_sets_cache_on_miss() -> None:
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_DummyResult([PermissionName.ROLES_READ]))
    redis_client = AsyncMock()
    redis_client.get_cached_user_permissions = AsyncMock(return_value=None)
    redis_client.set_cached_user_permissions = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)

    permissions = await service.get_user_permissions(user_id)

    assert permissions == {PermissionName.ROLES_READ}
    db.execute.assert_awaited_once()
    redis_client.set_cached_user_permissions.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_user_permissions_falls_back_to_db_when_cache_payload_invalid() -> (
    None
):
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_DummyResult([PermissionName.PERMISSIONS_READ]))
    redis_client = AsyncMock()
    redis_client.get_cached_user_permissions = AsyncMock(
        side_effect=ValueError("invalid payload")
    )
    redis_client.set_cached_user_permissions = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)

    permissions = await service.get_user_permissions(user_id)

    assert permissions == {PermissionName.PERMISSIONS_READ}
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_has_permission_uses_get_user_permissions_result() -> None:
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_DummyScalarResult(False))
    redis_client = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)
    service.get_user_permissions = AsyncMock(  # type: ignore[method-assign]
        return_value={PermissionName.ROLES_ASSIGN}
    )

    assert await service.has_permission(user_id, PermissionName.ROLES_ASSIGN) is True
    assert await service.has_permission(user_id, PermissionName.ROLES_DELETE) is False


@pytest.mark.asyncio
async def test_has_permission_allows_superuser_without_permission_lookup() -> None:
    user_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_DummyScalarResult(True))
    redis_client = AsyncMock()
    service = PermissionCheckService(db=db, redis_client=redis_client)
    service.get_user_permissions = AsyncMock(  # type: ignore[method-assign]
        return_value=set()
    )

    assert await service.has_permission(user_id, PermissionName.ROLES_DELETE) is True
    service.get_user_permissions.assert_not_awaited()


@pytest.mark.asyncio
async def test_invalidate_user_permissions_cache_calls_redis_delete() -> None:
    user_id = uuid4()
    redis_client = AsyncMock()
    redis_client.invalidate_user_permissions_cache = AsyncMock()

    await invalidate_user_permissions_cache(redis_client, user_id)

    redis_client.invalidate_user_permissions_cache.assert_awaited_once_with(user_id)
