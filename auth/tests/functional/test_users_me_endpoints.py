from uuid import UUID

import pytest

from src.core.permissions import PermissionName
from src.main import app
from src.services.permission_check import get_permission_check_service


class _FakePermissionCheckService:
    """Fake permission checker used by /users/me permission tests."""

    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[UUID, PermissionName]] = []

    async def has_permission(self, user_id: UUID, permission: PermissionName) -> bool:
        self.calls.append((user_id, permission))
        return self.allowed


@pytest.mark.asyncio
async def test_me_returns_404_when_user_not_found(test_client) -> None:
    """Ensure `/users/me` returns 404 for missing user subject."""
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.get(
        "/api/v1/users/me",
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_users_me_change_email_returns_204(test_client) -> None:
    """Ensure current user email can be changed successfully."""
    response = await test_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "updated@example.com"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 204
    assert test_client.fake_user_service.changed_email == "updated@example.com"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_users_me_change_email_duplicate_returns_409(test_client) -> None:
    """Ensure duplicate email update returns conflict."""
    response = await test_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "duplicate@example.com"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists"


@pytest.mark.asyncio
async def test_users_me_change_email_returns_404_when_user_not_found(
    test_client,
) -> None:
    """Ensure email update returns 404 for unknown user."""
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "updated@example.com"},
        headers={"X-Request-Id": "test-req-id"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_users_me_change_email_non_fresh_token_returns_401(
    test_client,
) -> None:
    """Ensure email update requires fresh access token."""
    test_client.fake_auth.is_fresh = False  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/email",
        json={"new_email": "updated@example.com"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Fresh token required"


@pytest.mark.asyncio
async def test_users_me_change_password_returns_204(test_client) -> None:
    """Ensure current user password can be changed successfully."""
    response = await test_client.patch(
        "/api/v1/users/me/password",
        json={"new_password": "StrongPass1!"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 204
    assert test_client.fake_user_service.changed_password == "StrongPass1!"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_users_me_change_password_returns_404_when_user_not_found(
    test_client,
) -> None:
    """Ensure password update returns 404 for unknown user."""
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/password",
        json={"new_password": "StrongPass1!"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_users_me_change_password_non_fresh_token_returns_401(
    test_client,
) -> None:
    """Ensure password update requires fresh access token."""
    test_client.fake_auth.is_fresh = False  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/password",
        json={"new_password": "StrongPass1!"},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Fresh token required"


@pytest.mark.asyncio
async def test_users_me_logs_returns_paginated_logs(test_client) -> None:
    """Ensure logs endpoint supports pagination."""
    response = await test_client.get(
        "/api/v1/users/me/logs",
        params={"page_size": 1, "page_number": 0},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["log_type"] == "login"
    assert body[0]["created_at"].endswith("Z")


@pytest.mark.asyncio
async def test_users_me_logs_are_sorted_newest_first(test_client) -> None:
    """Ensure user logs are returned in descending creation order."""
    response = await test_client.get(
        "/api/v1/users/me/logs",
        params={"page_size": 10, "page_number": 0},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 2
    assert body[0]["created_at"] > body[1]["created_at"]


@pytest.mark.asyncio
async def test_users_me_logs_returns_empty_for_out_of_range_page(test_client) -> None:
    """Ensure logs endpoint returns empty list for out-of-range page."""
    response = await test_client.get(
        "/api/v1/users/me/logs",
        params={"page_size": 10, "page_number": 1},
        headers={"X-Request-Id": "test-req-id"},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_users_me_logs_unauthorized_returns_401(test_client) -> None:
    """Ensure logs endpoint requires authentication."""
    test_client.fake_auth.is_authorized = False  # type: ignore[attr-defined]

    response = await test_client.get(
        "/api/v1/users/me/logs", headers={"X-Request-Id": "test-req-id"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


@pytest.mark.asyncio
async def test_users_me_has_permission_returns_boolean(test_client) -> None:
    """Ensure permission check endpoint returns boolean payload."""
    fake_permission_check_service = _FakePermissionCheckService(allowed=True)
    app.dependency_overrides[get_permission_check_service] = lambda: (
        fake_permission_check_service
    )

    try:
        response = await test_client.get(
            "/api/v1/users/me/has_permission/roles:read",
            headers={"X-Request-Id": "test-req-id"},
        )

        assert response.status_code == 200
        assert response.json() == {"has_permission": True}
        assert fake_permission_check_service.calls
        _, checked_permission = fake_permission_check_service.calls[0]
        assert checked_permission == PermissionName.ROLES_READ
    finally:
        app.dependency_overrides.pop(get_permission_check_service, None)


@pytest.mark.asyncio
async def test_users_me_has_permission_invalid_name_returns_422(test_client) -> None:
    """Ensure invalid permission name is rejected by validation."""
    fake_permission_check_service = _FakePermissionCheckService(allowed=True)
    app.dependency_overrides[get_permission_check_service] = lambda: (
        fake_permission_check_service
    )

    try:
        response = await test_client.get(
            "/api/v1/users/me/has_permission/not-a-permission",
            headers={"X-Request-Id": "test-req-id"},
        )

        assert response.status_code == 422
        assert fake_permission_check_service.calls == []
    finally:
        app.dependency_overrides.pop(get_permission_check_service, None)
