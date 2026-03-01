import pytest


@pytest.mark.asyncio
async def test_signup_returns_201(test_client) -> None:
    response = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "login": "newuser",
            "password": "StrongPass1!",
            "first_name": "Petr",
            "last_name": "Petrov",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["first_name"] == "Petr"
    assert body["last_name"] == "Petrov"


@pytest.mark.asyncio
async def test_signup_duplicate_returns_409(test_client) -> None:
    response = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "login": "duplicate",
            "password": "StrongPass1!",
            "first_name": "Petr",
            "last_name": "Petrov",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this login already exists"


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(test_client) -> None:
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"login": "bad", "password": "bad"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid login or password"


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(test_client) -> None:
    response = await test_client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_revoke_adds_jti_to_blacklist(test_client) -> None:
    response = await test_client.delete("/api/v1/auth/refresh-revoke")

    assert response.status_code == 204
    assert test_client.fake_token_service.last_refresh_blacklisted_jti == "refresh-jti"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_access_revoke_adds_jti_to_blacklist(test_client) -> None:
    response = await test_client.delete("/api/v1/auth/access-revoke")

    assert response.status_code == 204
    assert test_client.fake_token_service.last_access_blacklisted_jti == "refresh-jti"  # type: ignore[attr-defined]
