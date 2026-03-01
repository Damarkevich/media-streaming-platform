import pytest


@pytest.mark.asyncio
async def test_me_returns_404_when_user_not_found(test_client) -> None:
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.get("/api/v1/users/me")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_users_me_change_login_returns_204(test_client) -> None:
    response = await test_client.patch(
        "/api/v1/users/me/login",
        json={"new_login": "updatedlogin"},
    )

    assert response.status_code == 204
    assert test_client.fake_user_service.changed_login == "updatedlogin"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_users_me_change_login_duplicate_returns_409(test_client) -> None:
    response = await test_client.patch(
        "/api/v1/users/me/login",
        json={"new_login": "duplicate"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this login already exists"


@pytest.mark.asyncio
async def test_users_me_change_login_returns_404_when_user_not_found(
    test_client,
) -> None:
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/login",
        json={"new_login": "updatedlogin"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_users_me_change_password_returns_204(test_client) -> None:
    response = await test_client.patch(
        "/api/v1/users/me/password",
        json={"new_password": "StrongPass1!"},
    )

    assert response.status_code == 204
    assert test_client.fake_user_service.changed_password == "StrongPass1!"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_users_me_change_password_returns_404_when_user_not_found(
    test_client,
) -> None:
    test_client.fake_auth.subject = "00000000-0000-0000-0000-000000000000"  # type: ignore[attr-defined]

    response = await test_client.patch(
        "/api/v1/users/me/password",
        json={"new_password": "StrongPass1!"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
