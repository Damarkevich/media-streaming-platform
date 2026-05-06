"""Tests for src.services.auth_client."""

from unittest.mock import AsyncMock, MagicMock, patch


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

    async def test_returns_none_on_network_error(self):
        from src.services.auth_client import get_user

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("connection refused"))

        with patch("src.services.auth_client.get_http_client", return_value=mock_client):
            result = await get_user("some-user")

        assert result is None

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
