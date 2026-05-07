"""Tests for src.services.email."""
from unittest.mock import AsyncMock, MagicMock, patch


class TestSendEmail:
    async def test_returns_true_on_success(self):
        from src.services.email import send_email

        mock_transactional = AsyncMock()
        mock_transactional.send_transac_email = AsyncMock(return_value=None)
        mock_client = MagicMock()
        mock_client.transactional_emails = mock_transactional

        with patch("src.services.email.get_brevo_client", return_value=mock_client):
            result = await send_email(
                to_email="test@example.com",
                to_name="Test User",
                subject="Hello",
                html_content="<p>Hi</p>",
            )

        assert result is True
        mock_transactional.send_transac_email.assert_called_once()

    async def test_returns_false_on_brevo_exception(self):
        from src.services.email import send_email

        mock_transactional = AsyncMock()
        mock_transactional.send_transac_email = AsyncMock(
            side_effect=Exception("Brevo API error")
        )
        mock_client = MagicMock()
        mock_client.transactional_emails = mock_transactional

        with patch("src.services.email.get_brevo_client", return_value=mock_client):
            result = await send_email(
                to_email="fail@example.com",
                to_name="Fail User",
                subject="Subject",
                html_content="<p>Body</p>",
            )

        assert result is False

    async def test_returns_false_on_brevo_timeout(self):
        from src.services.email import send_email

        mock_transactional = AsyncMock()
        mock_transactional.send_transac_email = AsyncMock(side_effect=TimeoutError)
        mock_client = MagicMock()
        mock_client.transactional_emails = mock_transactional

        with patch("src.services.email.get_brevo_client", return_value=mock_client):
            result = await send_email(
                to_email="timeout@example.com",
                to_name="Timeout User",
                subject="Subject",
                html_content="<p>Body</p>",
            )

        assert result is False

    async def test_sends_correct_recipient(self):
        from src.services.email import send_email

        captured = {}
        mock_transactional = AsyncMock()

        async def capture(**kwargs):
            captured.update(kwargs)

        mock_transactional.send_transac_email = capture
        mock_client = MagicMock()
        mock_client.transactional_emails = mock_transactional

        with patch("src.services.email.get_brevo_client", return_value=mock_client):
            await send_email(
                to_email="alice@example.com",
                to_name="Alice",
                subject="Test",
                html_content="<p>Test</p>",
            )

        recipients = captured.get("to", [])
        assert len(recipients) == 1
        assert recipients[0].email == "alice@example.com"
        assert recipients[0].name == "Alice"
        assert captured.get("subject") == "Test"
        assert "request_options" not in captured


class TestGetBrevoClient:
    def test_uses_configured_client_timeout(self):
        import src.services.email as email_module

        email_module._client = None
        with patch("src.services.email.brevo.AsyncBrevo") as mock_brevo:
            email_module.get_brevo_client()

        mock_brevo.assert_called_once_with(
            api_key=email_module.settings.brevo_api_key,
            timeout=email_module.settings.brevo_timeout_seconds,
        )
        email_module._client = None


class TestCloseBrevoClient:
    async def test_closes_aclose_when_initialized(self):
        import src.services.email as email_module

        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        email_module._client = mock_client

        await email_module.close_brevo_client()

        mock_client.aclose.assert_called_once()
        assert email_module._client is None

    async def test_noop_when_not_initialized(self):
        import src.services.email as email_module

        email_module._client = None
        await email_module.close_brevo_client()
        assert email_module._client is None

