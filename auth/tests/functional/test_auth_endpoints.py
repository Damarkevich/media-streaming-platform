import pytest

from src.core.config import settings
from src.models.log import LogType


@pytest.mark.asyncio
async def test_signup_returns_201(test_client) -> None:
    """Ensure signup returns 201 and user profile payload."""
    response = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newuser@example.com",
            "password": "StrongPass1!",
            "first_name": "Petr",
            "last_name": "Petrov",
        },
        headers={"X-Request-Id": "test-req-1"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["first_name"] == "Petr"
    assert body["last_name"] == "Petrov"


@pytest.mark.asyncio
async def test_signup_duplicate_returns_409(test_client) -> None:
    """Ensure duplicate signup returns conflict error."""
    response = await test_client.post(
        "/api/v1/auth/signup",
        json={
            "email": "duplicate@example.com",
            "password": "StrongPass1!",
            "first_name": "Petr",
            "last_name": "Petrov",
        },
        headers={"X-Request-Id": "test-req-2"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "User with this email already exists"


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(test_client) -> None:
    """Ensure login with invalid credentials is rejected."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "bad@example.com", "password": "bad"},
        headers={"X-Request-Id": "test-req-3"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_success_returns_tokens_and_logs_action(test_client) -> None:
    """Ensure successful login returns token pair and writes login log."""
    response = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "valid@example.com", "password": "ValidPass1!"},
        headers={"X-Request-Id": "test-req-4"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert test_client.fake_user_service.last_logged_user_id == str(  # type: ignore[attr-defined]
        test_client.fake_user_service.authenticated_user_id  # type: ignore[attr-defined]
    )
    assert test_client.fake_user_service.last_logged_type == LogType.LOGIN  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_login_rate_limit_returns_429_after_five_requests(test_client) -> None:
    """Ensure login endpoint enforces configured per-minute request limit."""
    statuses: list[int] = []

    for i in range(6):
        response = await test_client.post(
            "/api/v1/auth/login",
            json={"email": "valid@example.com", "password": "ValidPass1!"},
            headers={"X-Request-Id": f"test-req-rl-{i}"},
        )
        statuses.append(response.status_code)

    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429


@pytest.mark.asyncio
async def test_refresh_is_not_rate_limited_without_decorator(test_client) -> None:
    """Ensure endpoints without limiter decorator are not throttled by middleware."""
    statuses: list[int] = []

    for i in range(6):
        response = await test_client.post(
            "/api/v1/auth/refresh",
            headers={"X-Request-Id": f"test-req-refresh-{i}"},
        )
        statuses.append(response.status_code)

    assert statuses == [200, 200, 200, 200, 200, 200]


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(test_client) -> None:
    """Ensure refresh endpoint returns new access and refresh tokens."""
    response = await test_client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "test-req-refresh-main"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_revoke_adds_jti_to_blacklist(test_client) -> None:
    """Ensure refresh revoke stores token JTI in blacklist."""
    response = await test_client.delete(
        "/api/v1/auth/refresh-revoke",
        headers={"X-Request-Id": "test-req-refresh-revoke"},
    )

    assert response.status_code == 204
    assert test_client.fake_token_service.last_refresh_blacklisted_jti == "refresh-jti"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_access_revoke_adds_jti_to_blacklist(test_client) -> None:
    """Ensure access revoke stores token JTI in blacklist."""
    response = await test_client.delete(
        "/api/v1/auth/access-revoke",
        headers={"X-Request-Id": "test-req-access-revoke"},
    )

    assert response.status_code == 204
    assert test_client.fake_token_service.last_access_blacklisted_jti == "refresh-jti"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cors_preflight_allows_configured_origin(test_client) -> None:
    """Ensure CORS preflight succeeds for configured origins."""
    allowed_origin = settings.cors_origins[0]

    response = await test_client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "POST",
            "X-Request-Id": "test-req-cors-1",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in {
        allowed_origin,
        "*",
    }
    if "*" in settings.cors_origins:
        assert "access-control-allow-credentials" not in response.headers
    else:
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_preflight_rejects_unconfigured_origin_when_not_wildcard(
    test_client,
) -> None:
    """Ensure disallowed origins are rejected when CORS is not wildcard-based."""
    if "*" in settings.cors_origins:
        pytest.skip("Wildcard CORS configured; any origin is allowed.")

    disallowed_origin = "http://evil.example.com"
    if disallowed_origin in settings.cors_origins:
        disallowed_origin = "http://another-evil.example.com"

    response = await test_client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": disallowed_origin,
            "Access-Control-Request-Method": "POST",
            "X-Request-Id": "test-req-cors-2",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
