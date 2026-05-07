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
            patch("src.consumers.delivery.notification_sender.send_notification", new_callable=AsyncMock) as mock_send,
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

        async def send_notification_side_effect(*args, **kwargs):
            trace.append("send")
            return True

        with (
            patch("src.consumers.delivery.async_session", return_value=mock_ctx),
            patch(
                "src.consumers.delivery.idempotency.reserve_key",
                side_effect=reserve_side_effect,
            ),
            patch("src.consumers.delivery.notification_sender.send_notification", new_callable=AsyncMock, side_effect=send_notification_side_effect) as mock_send_notification,
        ):
            await _handle(_payload(), AsyncMock())

        assert trace == ["reserve", "send"]
        mock_send_notification.assert_called_once()

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

        await_args = mock_finalize.await_args
        assert await_args is not None
        assert await_args.kwargs["status"] == "FAILED"
        assert await_args.kwargs["error"] == "Template not found"
        mock_dlq.assert_called_once()


class TestProcessMessage:
    async def test_sends_domain_errors_to_dlq(self):
        from src.consumers.delivery import _process_message

        payload = _payload()
        with (
            patch(
                "src.consumers.delivery._handle",
                new_callable=AsyncMock,
                side_effect=ValueError("bad payload"),
            ),
            patch(
                "src.consumers.delivery._publish_dlq",
                new_callable=AsyncMock,
            ) as mock_dlq,
        ):
            should_commit = await _process_message(payload, AsyncMock())

        assert should_commit is True
        await_args = mock_dlq.await_args
        assert await_args is not None
        assert "domain_error:ValueError" in await_args.args[2]

    async def test_retries_then_sends_to_dlq(self):
        from sqlalchemy.exc import OperationalError

        from src.consumers.delivery import _process_message

        payload = _payload()

        with (
            patch("src.consumers.delivery.settings.consumer_max_retries", 2),
            patch("src.consumers.delivery.settings.consumer_retry_delay_seconds", 0.0),
            patch(
                "src.consumers.delivery._handle",
                new_callable=AsyncMock,
                side_effect=OperationalError("SELECT 1", {}, Exception("db down")),
            ) as mock_handle,
            patch(
                "src.consumers.delivery._publish_dlq",
                new_callable=AsyncMock,
            ) as mock_dlq,
            patch("src.consumers.delivery.asyncio.sleep", new_callable=AsyncMock),
        ):
            should_commit = await _process_message(payload, AsyncMock())

        assert should_commit is True
        assert mock_handle.await_count == 2
        await_args = mock_dlq.await_args
        assert await_args is not None
        assert "retry_exhausted:OperationalError" in await_args.args[2]
