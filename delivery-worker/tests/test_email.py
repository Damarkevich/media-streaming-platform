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

