from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from src.core.permissions import PermissionName
from src.main import app
from src.services.permission_check import get_permission_check_service
from src.services.roles import get_role_service


class FakeRoleService:
    def __init__(self, roles: list[SimpleNamespace]) -> None:
        self.roles = roles

    async def get_roles(
        self, page_size: int, page_number: int
    ) -> list[SimpleNamespace]:
        offset = page_number * page_size
        return self.roles[offset : offset + page_size]

    async def get_role_by_id(self, role_id: UUID) -> SimpleNamespace | None:
        for role in self.roles:
            if role.id == role_id:
                return role
        return None

    async def create_role(self, name: str) -> SimpleNamespace:
        role = SimpleNamespace(id=uuid4(), name=name)
        self.roles.append(role)
        return role

    async def update_role(self, role_id: UUID, new_name: str) -> bool:
        for role in self.roles:
            if role.id == role_id:
                role.name = new_name
                return True
        return False

    async def delete_role(self, role_id: UUID) -> bool:
        before = len(self.roles)
        self.roles = [role for role in self.roles if role.id != role_id]
        return len(self.roles) != before

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        return None

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        return None


class FakePermissionService:
    def __init__(self, permissions: list[SimpleNamespace]) -> None:
        self.permissions = permissions

    async def get_permissions(
        self, page_size: int, page_number: int
    ) -> list[SimpleNamespace]:
        offset = page_number * page_size
        return self.permissions[offset : offset + page_size]

    async def get_permissions_by_role_id(self, role_id: UUID) -> list[SimpleNamespace]:
        return self.permissions

    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        return None

    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        return None


class FakePermissionCheckService:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[UUID, PermissionName]] = []

    async def has_permission(self, user_id: UUID, permission: PermissionName) -> bool:
        self.calls.append((user_id, permission))
        return self.allowed


def _override_services(
    *,
    role_service: FakeRoleService,
    permission_service: FakePermissionService,
    permission_check_service: FakePermissionCheckService,
) -> None:
    from src.services.permissions import get_permission_service

    app.dependency_overrides[get_role_service] = lambda: role_service
    app.dependency_overrides[get_permission_service] = lambda: permission_service
    app.dependency_overrides[get_permission_check_service] = lambda: (
        permission_check_service
    )


@pytest.mark.asyncio
async def test_get_roles_returns_403_when_roles_read_permission_missing(
    test_client: AsyncClient,
) -> None:
    fake_role_service = FakeRoleService(
        roles=[SimpleNamespace(id=uuid4(), name="admin")]
    )
    fake_permission_service = FakePermissionService(
        permissions=[SimpleNamespace(id=uuid4(), name=PermissionName.PERMISSIONS_READ)]
    )
    fake_permission_check_service = FakePermissionCheckService(allowed=False)

    _override_services(
        role_service=fake_role_service,
        permission_service=fake_permission_service,
        permission_check_service=fake_permission_check_service,
    )

    response = await test_client.get("/api/v1/roles")

    assert response.status_code == 403
    assert response.json()["detail"] == "Permission 'roles:read' is required"
    assert fake_permission_check_service.calls
    _, checked_permission = fake_permission_check_service.calls[0]
    assert checked_permission == PermissionName.ROLES_READ


@pytest.mark.asyncio
async def test_get_roles_returns_200_when_roles_read_permission_present(
    test_client: AsyncClient,
) -> None:
    role_id = uuid4()
    fake_role_service = FakeRoleService(
        roles=[SimpleNamespace(id=role_id, name="admin")]
    )
    fake_permission_service = FakePermissionService(
        permissions=[SimpleNamespace(id=uuid4(), name=PermissionName.PERMISSIONS_READ)]
    )
    fake_permission_check_service = FakePermissionCheckService(allowed=True)

    _override_services(
        role_service=fake_role_service,
        permission_service=fake_permission_service,
        permission_check_service=fake_permission_check_service,
    )

    response = await test_client.get("/api/v1/roles")

    assert response.status_code == 200
    assert response.json() == [{"id": str(role_id), "name": "admin"}]
    assert fake_permission_check_service.calls
    _, checked_permission = fake_permission_check_service.calls[0]
    assert checked_permission == PermissionName.ROLES_READ


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "url", "payload", "expected_permission"),
    [
        (
            "GET",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001",
            None,
            PermissionName.ROLES_READ,
        ),
        ("POST", "/api/v1/roles", {"name": "editor"}, PermissionName.ROLES_CREATE),
        (
            "PATCH",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001",
            {"name": "updated"},
            PermissionName.ROLES_UPDATE,
        ),
        (
            "DELETE",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001",
            None,
            PermissionName.ROLES_DELETE,
        ),
        (
            "GET",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001/permissions",
            None,
            PermissionName.PERMISSIONS_READ,
        ),
        (
            "PUT",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001/users/00000000-0000-0000-0000-000000000002",
            None,
            PermissionName.ROLES_ASSIGN,
        ),
        (
            "DELETE",
            "/api/v1/roles/00000000-0000-0000-0000-000000000001/users/00000000-0000-0000-0000-000000000002",
            None,
            PermissionName.ROLES_ASSIGN,
        ),
        ("GET", "/api/v1/permissions", None, PermissionName.PERMISSIONS_READ),
        (
            "PUT",
            "/api/v1/permissions/00000000-0000-0000-0000-000000000003/roles/00000000-0000-0000-0000-000000000001",
            None,
            PermissionName.PERMISSIONS_ASSIGN,
        ),
        (
            "DELETE",
            "/api/v1/permissions/00000000-0000-0000-0000-000000000003/roles/00000000-0000-0000-0000-000000000001",
            None,
            PermissionName.PERMISSIONS_ASSIGN,
        ),
    ],
)
async def test_roles_and_permissions_endpoints_return_403_without_permission(
    test_client: AsyncClient,
    method: str,
    url: str,
    payload: dict[str, str] | None,
    expected_permission: PermissionName,
) -> None:
    role_id = uuid4()
    fake_role_service = FakeRoleService(
        roles=[SimpleNamespace(id=role_id, name="admin")]
    )
    fake_permission_service = FakePermissionService(
        permissions=[SimpleNamespace(id=uuid4(), name=PermissionName.PERMISSIONS_READ)]
    )
    fake_permission_check_service = FakePermissionCheckService(allowed=False)

    _override_services(
        role_service=fake_role_service,
        permission_service=fake_permission_service,
        permission_check_service=fake_permission_check_service,
    )

    response = await test_client.request(method, url, json=payload)

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == f"Permission '{expected_permission.value}' is required"
    )
    assert fake_permission_check_service.calls
    _, checked_permission = fake_permission_check_service.calls[0]
    assert checked_permission == expected_permission
