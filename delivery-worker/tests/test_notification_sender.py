"""Tests for src.services.notification_sender."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch


class TestSendNotification:
    async def test_returns_true_on_successful_send(self):
        """Happy path: user found, template rendered, email sent, delivery recorded."""
        from src.services.notification_sender import send_notification

        mock_session = AsyncMock()

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
        ):
            mock_get_user.return_value = {
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
            }
            mock_render.return_value = ("Subject: Hello", "<p>Body</p>")
            mock_send_email.return_value = True
            mock_finalize.return_value = None

            result = await send_notification(
                session=mock_session,
                user_id="user-123",
                template={"subject_template": "Hello {{first_name}}", "body_template": "Body"},
                variables={"custom": "value"},
                idempotency_key="key-123",
            )

        assert result is True
        mock_get_user.assert_called_once_with("user-123")
        mock_render.assert_called_once()
        mock_send_email.assert_called_once_with("user@example.com", "John Doe", "Subject: Hello", "<p>Body</p>")
        mock_finalize.assert_called_once()
        await_kwargs = mock_finalize.await_args.kwargs
        assert await_kwargs["status"] == "SENT"
        assert await_kwargs["error"] is None
        assert await_kwargs["session"] == mock_session

    async def test_returns_true_when_no_name_fallback_to_email(self):
        """When user has no first/last name, use email as to_name."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key"),
        ):
            mock_get_user.return_value = {
                "email": "user@example.com",
                "first_name": "",
                "last_name": "",
            }
            mock_render.return_value = ("Subject", "Body")
            mock_send_email.return_value = True

            result = await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )

        assert result is True
        # Verify to_name was set to email
        call_args = mock_send_email.await_args
        assert call_args[0][1] == "user@example.com"

    async def test_returns_false_when_user_not_found(self):
        """User not found → finalize with FAILED status → return False."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
        ):
            mock_get_user.return_value = None
            mock_finalize.return_value = None

            result = await send_notification(
                user_id="nonexistent-user",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )

        assert result is False
        mock_send_email.assert_not_called()
        await_kwargs = mock_finalize.await_args.kwargs
        assert await_kwargs["status"] == "FAILED"
        assert await_kwargs["error"] == "User not found"

    async def test_returns_false_when_send_fails(self):
        """Email send returns False → finalize with FAILED status → return False."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
        ):
            mock_get_user.return_value = {"email": "u@example.com", "first_name": "A", "last_name": "B"}
            mock_render.return_value = ("Subject", "Body")
            mock_send_email.return_value = False
            mock_finalize.return_value = None

            result = await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )

        assert result is False
        await_kwargs = mock_finalize.await_args.kwargs
        assert await_kwargs["status"] == "FAILED"
        assert await_kwargs["error"] == "Brevo send_transac_email returned error"

    async def test_handles_render_exception(self):
        """Template render exception → finalize with FAILED → return False."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
        ):
            mock_get_user.return_value = {"email": "u@example.com", "first_name": "A", "last_name": "B"}
            mock_render.side_effect = ValueError("Invalid template")
            mock_finalize.return_value = None

            result = await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )

        assert result is False
        mock_send_email.assert_not_called()
        await_kwargs = mock_finalize.await_args.kwargs
        assert await_kwargs["status"] == "FAILED"
        assert "Template render failed" in await_kwargs["error"]

    async def test_builds_variables_with_name_and_user_variables(self):
        """Verify that first_name/last_name are merged with user-provided variables."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key"),
        ):
            mock_get_user.return_value = {"email": "u@example.com", "first_name": "John", "last_name": "Doe"}
            mock_render.return_value = ("Subject", "Body")
            mock_send_email.return_value = True

            await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={"review_id": "rev-123", "likes_count": 5},
                idempotency_key="key-123",
            )

        # Check that render was called with merged variables
        render_call = mock_render.call_args
        render_vars = render_call[0][2]
        assert render_vars["first_name"] == "John"
        assert render_vars["last_name"] == "Doe"
        assert render_vars["review_id"] == "rev-123"
        assert render_vars["likes_count"] == 5

    async def test_sent_at_only_set_on_success(self):
        """Verify sent_at is set to current datetime only when send succeeds."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
        ):
            mock_get_user.return_value = {"email": "u@example.com", "first_name": "A", "last_name": "B"}
            mock_render.return_value = ("Subject", "Body")
            mock_send_email.return_value = True
            mock_finalize.return_value = None

            before = datetime.now(UTC)
            await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )
            after = datetime.now(UTC)

            await_kwargs = mock_finalize.await_args.kwargs
            assert await_kwargs["sent_at"] is not None
            assert before <= await_kwargs["sent_at"] <= after

    async def test_sent_at_none_on_failure(self):
        """Verify sent_at remains None when send fails."""
        from src.services.notification_sender import send_notification

        with (
            patch("src.services.notification_sender.auth_client.get_user") as mock_get_user,
            patch("src.services.notification_sender.template_renderer.render") as mock_render,
            patch("src.services.notification_sender.email.send_email") as mock_send_email,
            patch("src.services.notification_sender.idempotency.finalize_key") as mock_finalize,
        ):
            mock_get_user.return_value = {"email": "u@example.com", "first_name": "A", "last_name": "B"}
            mock_render.return_value = ("Subject", "Body")
            mock_send_email.return_value = False
            mock_finalize.return_value = None

            await send_notification(
                user_id="user-123",
                template={"subject_template": "Hi", "body_template": "Body"},
                variables={},
                idempotency_key="key-123",
            )

            await_kwargs = mock_finalize.await_args.kwargs
            assert await_kwargs["sent_at"] is None
