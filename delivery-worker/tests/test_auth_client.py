"""Tests for src.services.auth_client."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


class TestGetUser:
    async def test_returns_user_dict_on_success(self):
        from src.services.auth_client import get_user

        expected = {"user_id": "abc", "email": "a@b.com"}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = expected
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            result = await get_user("abc")

        assert result == expected

    async def test_returns_none_on_404(self):
        from src.services.auth_client import get_user

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            result = await get_user("nonexistent")

        assert result is None

    async def test_raises_on_network_error(self):
        from src.services.auth_client import get_user

        mock_client = MagicMock()
        request = httpx.Request("GET", "http://test-auth:8000/api/v1/users/internal/some-user")
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("connection refused", request=request)
        )

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            with pytest.raises(httpx.HTTPError):
                await get_user("some-user")

    async def test_sends_internal_key_header(self):
        from src.services.auth_client import get_user

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            await get_user("uid-1")

        call_kwargs = mock_client.get.call_args[1]
        assert "X-Internal-Key" in call_kwargs.get("headers", {})

    async def test_url_contains_user_id(self):
        from src.services.auth_client import get_user

        user_id = "user-xyz"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            await get_user(user_id)

        call_url = mock_client.get.call_args[0][0]
        assert user_id in call_url


class TestGetHttpClient:
    async def test_uses_configured_timeout(self):
        import src.services.auth_client as auth_client_module

        auth_client_module._client = None  # reset singleton for deterministic test
        client = auth_client_module.get_http_client()
        try:
            from src.core.config import settings

            assert client.timeout.connect == settings.auth_http_timeout_seconds
            assert client.timeout.read == settings.auth_http_timeout_seconds
            assert client.timeout.write == settings.auth_http_timeout_seconds
            assert client.timeout.pool == settings.auth_http_timeout_seconds
        finally:
            await client.aclose()
            auth_client_module._client = None
