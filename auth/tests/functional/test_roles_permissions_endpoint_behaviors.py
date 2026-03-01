from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from src.core.permissions import PermissionName
from src.main import app
from src.services.permission_check import get_permission_check_service
from src.services.permissions import (
    PermissionNotFoundError,
    get_permission_service,
)
from src.services.permissions import (
    RoleNotFoundError as PermissionRoleNotFoundError,
)
from src.services.roles import (
    RoleAlreadyExistsError,
    UserNotFoundError,
    get_role_service,
)
from src.services.roles import (
    RoleNotFoundError as RoleServiceRoleNotFoundError,
)

MISSING_ROLE_ID = uuid4()
MISSING_USER_ID = uuid4()
MISSING_PERMISSION_ID = uuid4()


class _AllowPermissionCheckService:
    """Permission checker stub that always allows endpoint access."""

    async def has_permission(self, user_id: UUID, permission: PermissionName) -> bool:
        return True


class _RoleServiceStub:
    """Role-service stub for endpoint behavior tests."""

    def __init__(self) -> None:
        self.role_id = uuid4()

    async def get_roles(
        self, page_size: int, page_number: int
    ) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=self.role_id, name="admin")]

    async def get_role_by_id(self, role_id: UUID) -> SimpleNamespace | None:
        if role_id == MISSING_ROLE_ID:
            return None
        return SimpleNamespace(id=role_id, name="editor")

    async def create_role(self, name: str) -> SimpleNamespace:
        if name == "duplicate":
            raise RoleAlreadyExistsError("Role with this name already exists")
        return SimpleNamespace(id=uuid4(), name=name)

    async def update_role(self, role_id: UUID, new_name: str) -> bool:
        if new_name == "duplicate":
            raise RoleAlreadyExistsError("Role with this name already exists")
        return role_id != MISSING_ROLE_ID

    async def delete_role(self, role_id: UUID) -> bool:
        return role_id != MISSING_ROLE_ID

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        if role_id == MISSING_ROLE_ID:
            raise RoleServiceRoleNotFoundError("Role not found")
        if user_id == MISSING_USER_ID:
            raise UserNotFoundError("User not found")

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        if role_id == MISSING_ROLE_ID:
            raise RoleServiceRoleNotFoundError("Role not found")
        if user_id == MISSING_USER_ID:
            raise UserNotFoundError("User not found")


class _PermissionServiceStub:
    """Permission-service stub for endpoint behavior tests."""

    async def get_permissions(
        self, page_size: int, page_number: int
    ) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=uuid4(), name=PermissionName.PERMISSIONS_READ)]

    async def get_permissions_by_role_id(self, role_id: UUID) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=uuid4(), name=PermissionName.ROLES_READ)]

    async def assign_permission_to_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        if role_id == MISSING_ROLE_ID:
            raise PermissionRoleNotFoundError("Role not found")
        if permission_id == MISSING_PERMISSION_ID:
            raise PermissionNotFoundError("Permission not found")

    async def remove_permission_from_role(
        self, role_id: UUID, permission_id: UUID
    ) -> None:
        if role_id == MISSING_ROLE_ID:
            raise PermissionRoleNotFoundError("Role not found")
        if permission_id == MISSING_PERMISSION_ID:
            raise PermissionNotFoundError("Permission not found")


def _override_behavior_services() -> None:
    """Inject endpoint stubs that allow access and expose behavior branches."""
    app.dependency_overrides[get_permission_check_service] = lambda: (
        _AllowPermissionCheckService()
    )
    app.dependency_overrides[get_role_service] = lambda: _RoleServiceStub()
    app.dependency_overrides[get_permission_service] = lambda: _PermissionServiceStub()


@pytest.mark.asyncio
async def test_get_role_by_id_returns_404_when_missing(
    test_client: AsyncClient,
) -> None:
    """Ensure role lookup returns 404 when service has no role."""
    _override_behavior_services()

    response = await test_client.get(f"/api/v1/roles/{MISSING_ROLE_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"


@pytest.mark.asyncio
async def test_create_role_returns_409_on_duplicate_name(
    test_client: AsyncClient,
) -> None:
    """Ensure role create maps duplicate-name domain error to 409."""
    _override_behavior_services()

    response = await test_client.post("/api/v1/roles", json={"name": "duplicate"})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_role_returns_404_when_missing(test_client: AsyncClient) -> None:
    """Ensure role update returns 404 when target role does not exist."""
    _override_behavior_services()

    response = await test_client.patch(
        f"/api/v1/roles/{MISSING_ROLE_ID}",
        json={"name": "updated"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"


@pytest.mark.asyncio
async def test_update_role_returns_409_on_duplicate_name(
    test_client: AsyncClient,
) -> None:
    """Ensure role update maps duplicate-name domain error to 409."""
    _override_behavior_services()

    response = await test_client.patch(
        f"/api/v1/roles/{uuid4()}",
        json={"name": "duplicate"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_role_returns_404_when_missing(test_client: AsyncClient) -> None:
    """Ensure role delete returns 404 when target role does not exist."""
    _override_behavior_services()

    response = await test_client.delete(f"/api/v1/roles/{MISSING_ROLE_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"


@pytest.mark.asyncio
async def test_get_role_permissions_returns_permission_list(
    test_client: AsyncClient,
) -> None:
    """Ensure role permissions endpoint returns mapped payload."""
    _override_behavior_services()

    response = await test_client.get(f"/api/v1/roles/{uuid4()}/permissions")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == PermissionName.ROLES_READ


@pytest.mark.asyncio
async def test_assign_role_to_user_returns_404_for_missing_entities(
    test_client: AsyncClient,
) -> None:
    """Ensure role assignment maps service not-found errors to 404."""
    _override_behavior_services()

    response = await test_client.put(f"/api/v1/roles/{MISSING_ROLE_ID}/users/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"


@pytest.mark.asyncio
async def test_remove_role_from_user_returns_404_for_missing_entities(
    test_client: AsyncClient,
) -> None:
    """Ensure role removal maps service not-found errors to 404."""
    _override_behavior_services()

    response = await test_client.delete(
        f"/api/v1/roles/{uuid4()}/users/{MISSING_USER_ID}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_get_permissions_returns_list_payload(test_client: AsyncClient) -> None:
    """Ensure permissions list endpoint returns mapped permissions payload."""
    _override_behavior_services()

    response = await test_client.get("/api/v1/permissions")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == PermissionName.PERMISSIONS_READ


@pytest.mark.asyncio
async def test_assign_permission_to_role_returns_404_for_missing_entities(
    test_client: AsyncClient,
) -> None:
    """Ensure permission assignment maps service not-found errors to 404."""
    _override_behavior_services()

    response = await test_client.put(
        f"/api/v1/permissions/{MISSING_PERMISSION_ID}/roles/{uuid4()}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Permission not found"


@pytest.mark.asyncio
async def test_remove_permission_from_role_returns_404_for_missing_entities(
    test_client: AsyncClient,
) -> None:
    """Ensure permission removal maps service not-found errors to 404."""
    _override_behavior_services()

    response = await test_client.delete(
        f"/api/v1/permissions/{uuid4()}/roles/{MISSING_ROLE_ID}"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Role not found"
