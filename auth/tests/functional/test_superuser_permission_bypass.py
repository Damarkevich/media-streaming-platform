import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from src.core.jwt import auth_dep
from src.db.postgres import async_session, engine
from src.main import app
from src.services.redis import get_redis_client

pytestmark = pytest.mark.asyncio(loop_scope="module")


class _FakeAuth:
    def __init__(self, subject: str) -> None:
        self.subject = subject

    async def jwt_required(self) -> None:
        return None

    async def get_jwt_subject(self) -> str:
        return self.subject


class _FakeRedisClient:
    def __init__(self) -> None:
        self._storage: dict[str, set[str]] = {}

    async def get_cached_user_permissions(self, user_id: UUID) -> set[str] | None:
        return self._storage.get(str(user_id))

    async def set_cached_user_permissions(
        self,
        user_id: UUID,
        permissions: set[str],
        ttl_seconds: int,
    ) -> None:
        self._storage[str(user_id)] = set(permissions)

    async def invalidate_user_permissions_cache(self, user_id: UUID) -> None:
        self._storage.pop(str(user_id), None)


async def _create_superuser(user_id: str, login: str) -> None:
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO auth.users (
                    id,
                    login,
                    password,
                    first_name,
                    last_name,
                    created_at,
                    is_superuser
                )
                VALUES (
                    :id,
                    :login,
                    :password,
                    :first_name,
                    :last_name,
                    :created_at,
                    :is_superuser
                )
                """
            ),
            {
                "id": user_id,
                "login": login,
                "password": "test-password-hash",
                "first_name": "Super",
                "last_name": "User",
                "created_at": datetime.now(timezone.utc),
                "is_superuser": True,
            },
        )
        await session.commit()


async def _create_regular_user(user_id: str, login: str) -> None:
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO auth.users (
                    id,
                    login,
                    password,
                    first_name,
                    last_name,
                    created_at,
                    is_superuser
                )
                VALUES (
                    :id,
                    :login,
                    :password,
                    :first_name,
                    :last_name,
                    :created_at,
                    :is_superuser
                )
                """
            ),
            {
                "id": user_id,
                "login": login,
                "password": "test-password-hash",
                "first_name": "Regular",
                "last_name": "User",
                "created_at": datetime.now(timezone.utc),
                "is_superuser": False,
            },
        )
        await session.commit()


async def _delete_user(user_id: str) -> None:
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM auth.logs WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await session.execute(
            text("DELETE FROM auth.user_roles WHERE user_id = :uid"),
            {"uid": user_id},
        )
        await session.execute(
            text("DELETE FROM auth.users WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()


async def _delete_role_by_name(role_name: str) -> None:
    async with async_session() as session:
        await session.execute(
            text(
                """
                DELETE FROM auth.user_roles
                WHERE role_id IN (SELECT id FROM auth.roles WHERE name = :role_name)
                """
            ),
            {"role_name": role_name},
        )
        await session.execute(
            text(
                """
                DELETE FROM auth.role_permissions
                WHERE role_id IN (SELECT id FROM auth.roles WHERE name = :role_name)
                """
            ),
            {"role_name": role_name},
        )
        await session.execute(
            text("DELETE FROM auth.roles WHERE name = :role_name"),
            {"role_name": role_name},
        )
        await session.commit()


async def _create_role(role_name: str) -> str:
    role_id = str(uuid.uuid4())
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO auth.roles (id, name, created_at)
                VALUES (:id, :name, :created_at)
                """
            ),
            {
                "id": role_id,
                "name": role_name,
                "created_at": datetime.now(timezone.utc),
            },
        )
        await session.commit()
    return role_id


async def _create_permission(permission_name: str) -> str:
    permission_id = str(uuid.uuid4())
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO auth.permissions (id, name, created_at)
                VALUES (:id, :name, :created_at)
                """
            ),
            {
                "id": permission_id,
                "name": permission_name,
                "created_at": datetime.now(timezone.utc),
            },
        )
        await session.commit()
    return permission_id


async def _link_permission_to_role(role_id: str, permission_id: str) -> None:
    async with async_session() as session:
        await session.execute(
            text(
                """
                INSERT INTO auth.role_permissions (role_id, permission_id)
                VALUES (:role_id, :permission_id)
                """
            ),
            {
                "role_id": role_id,
                "permission_id": permission_id,
            },
        )
        await session.commit()


async def _delete_permission_by_name(permission_name: str) -> None:
    async with async_session() as session:
        await session.execute(
            text("DELETE FROM auth.permissions WHERE name = :permission_name"),
            {"permission_name": permission_name},
        )
        await session.commit()


async def test_superuser_bypasses_permission_checks_for_roles_endpoint() -> None:
    user_id = str(uuid.uuid4())
    login = f"super-{uuid.uuid4().hex[:10]}"

    await engine.dispose()

    await _create_superuser(user_id=user_id, login=login)

    app.dependency_overrides[auth_dep] = lambda: _FakeAuth(subject=user_id)
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedisClient()

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/roles")

        assert response.status_code == HTTPStatus.OK
        assert response.json() is not None
    finally:
        app.dependency_overrides.clear()
        await _delete_user(user_id)


async def test_superuser_bypasses_permission_checks_for_create_role_endpoint() -> None:
    user_id = str(uuid.uuid4())
    login = f"super-{uuid.uuid4().hex[:10]}"
    role_name = f"super-created-{uuid.uuid4().hex[:10]}"

    await engine.dispose()

    await _create_superuser(user_id=user_id, login=login)

    app.dependency_overrides[auth_dep] = lambda: _FakeAuth(subject=user_id)
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedisClient()

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/roles",
                json={"name": role_name},
            )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["name"] == role_name
    finally:
        app.dependency_overrides.clear()
        await _delete_role_by_name(role_name)
        await _delete_user(user_id)


async def test_superuser_bypasses_permission_checks_for_assign_role_endpoint() -> None:
    superuser_id = str(uuid.uuid4())
    superuser_login = f"super-{uuid.uuid4().hex[:10]}"
    target_user_id = str(uuid.uuid4())
    target_user_login = f"regular-{uuid.uuid4().hex[:10]}"
    role_name = f"assignable-{uuid.uuid4().hex[:10]}"

    await engine.dispose()

    await _create_superuser(user_id=superuser_id, login=superuser_login)
    await _create_regular_user(user_id=target_user_id, login=target_user_login)
    role_id = await _create_role(role_name)

    app.dependency_overrides[auth_dep] = lambda: _FakeAuth(subject=superuser_id)
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedisClient()

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                f"/api/v1/roles/{role_id}/users/{target_user_id}"
            )

        assert response.status_code == HTTPStatus.NO_CONTENT
    finally:
        app.dependency_overrides.clear()
        await _delete_role_by_name(role_name)
        await _delete_user(target_user_id)
        await _delete_user(superuser_id)


async def test_superuser_bypasses_permission_checks_for_remove_permission_endpoint() -> (
    None
):
    superuser_id = str(uuid.uuid4())
    superuser_login = f"super-{uuid.uuid4().hex[:10]}"
    role_name = f"perm-role-{uuid.uuid4().hex[:10]}"
    permission_name = f"perm-assign-{uuid.uuid4().hex[:10]}"

    await engine.dispose()

    await _create_superuser(user_id=superuser_id, login=superuser_login)
    role_id = await _create_role(role_name)
    permission_id = await _create_permission(permission_name)
    await _link_permission_to_role(role_id, permission_id)

    app.dependency_overrides[auth_dep] = lambda: _FakeAuth(subject=superuser_id)
    app.dependency_overrides[get_redis_client] = lambda: _FakeRedisClient()

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete(
                f"/api/v1/permissions/{permission_id}/roles/{role_id}"
            )

        assert response.status_code == HTTPStatus.NO_CONTENT
    finally:
        app.dependency_overrides.clear()
        await _delete_role_by_name(role_name)
        await _delete_permission_by_name(permission_name)
        await _delete_user(superuser_id)
