"""Tests for src.consumers.delivery._handle idempotency flow."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def _payload() -> dict:
    return {
        "campaign_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "template_id": str(uuid.uuid4()),
        "template_variables": {"custom_message": "hello"},
        "channel": "EMAIL",
        "idempotency_key": "campaign:test:user:test",
    }


def _template_result(subject: str = "Hi {{ first_name }}", body: str = "Body"):
    mappings = MagicMock()
    mappings.first.return_value = {
        "subject_template": subject,
        "body_template": body,
    }
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


class TestHandle:
    async def test_skips_when_idempotency_already_reserved(self):
        from src.consumers.delivery import _handle

        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.consumers.delivery.async_session", return_value=mock_ctx),
            patch(
                "src.consumers.delivery.idempotency.reserve_key",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch("src.consumers.delivery.email.send_email", new_callable=AsyncMock) as mock_send,
        ):
            await _handle(_payload(), AsyncMock())

        mock_send.assert_not_called()

    async def test_reserve_then_send_then_finalize_sent(self):
        from src.consumers.delivery import _handle

        trace: list[str] = []

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=_template_result())
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        async def reserve_side_effect(*args, **kwargs):
            trace.append("reserve")
            return True

        async def send_side_effect(*args, **kwargs):
            trace.append("send")
            return True

        async def finalize_side_effect(*args, **kwargs):
            trace.append("finalize")

        with (
            patch("src.consumers.delivery.async_session", return_value=mock_ctx),
            patch(
                "src.consumers.delivery.idempotency.reserve_key",
                side_effect=reserve_side_effect,
            ),
            patch("src.consumers.delivery.auth_client.get_user", new_callable=AsyncMock) as mock_get_user,
            patch("src.consumers.delivery.template_renderer.render") as mock_render,
            patch("src.consumers.delivery.email.send_email", side_effect=send_side_effect),
            patch(
                "src.consumers.delivery.idempotency.finalize_key",
                side_effect=finalize_side_effect,
            ) as mock_finalize,
        ):
            mock_get_user.return_value = {
                "email": "u@example.com",
                "first_name": "A",
                "last_name": "B",
            }
            mock_render.return_value = ("subject", "body")
            await _handle(_payload(), AsyncMock())

        assert trace == ["reserve", "send", "finalize"]
        assert mock_finalize.await_args.kwargs["status"] == "SENT"

    async def test_marks_failed_and_sends_dlq_when_template_missing(self):
        from src.consumers.delivery import _handle

        mappings = MagicMock()
        mappings.first.return_value = None
        result = MagicMock()
        result.mappings.return_value = mappings

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.consumers.delivery.async_session", return_value=mock_ctx),
            patch(
                "src.consumers.delivery.idempotency.reserve_key",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.consumers.delivery.idempotency.finalize_key",
                new_callable=AsyncMock,
            ) as mock_finalize,
            patch(
                "src.consumers.delivery._publish_dlq",
                new_callable=AsyncMock,
            ) as mock_dlq,
        ):
            await _handle(_payload(), AsyncMock())

        assert mock_finalize.await_args.kwargs["status"] == "FAILED"
        assert mock_finalize.await_args.kwargs["error"] == "Template not found"
        mock_dlq.assert_called_once()
