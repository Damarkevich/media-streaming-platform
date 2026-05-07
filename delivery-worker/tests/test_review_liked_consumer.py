"""Tests for src.consumers.review_liked._handle idempotency flow."""

from unittest.mock import AsyncMock, patch


def _payload() -> dict:
    return {
        "review_id": "review-1",
        "review_author_id": "author-1",
        "liker_user_id": "liker-1",
    }


class TestHandle:
    async def test_skips_when_idempotency_already_reserved(self):
        from src.consumers.review_liked import _handle

        with (
            patch(
                "src.consumers.review_liked.idempotency.reserve_key",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "src.consumers.review_liked.throttle.is_throttled",
                new_callable=AsyncMock,
            ) as mock_throttled,
        ):
            await _handle(_payload())

        mock_throttled.assert_not_called()

    async def test_throttled_updates_status_to_throttled(self):
        from src.consumers.review_liked import _handle

        with (
            patch(
                "src.consumers.review_liked.idempotency.reserve_key",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.consumers.review_liked.throttle.is_throttled",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "src.consumers.review_liked.idempotency.finalize_key",
                new_callable=AsyncMock,
            ) as mock_finalize,
        ):
            await _handle(_payload())

        assert mock_finalize.await_args.kwargs["status"] == "THROTTLED"

    async def test_reserve_then_send_then_finalize_sent(self):
        from src.consumers.review_liked import _handle

        trace: list[str] = []

        async def reserve_side_effect(*args, **kwargs):
            trace.append("reserve")
            return True

        async def send_side_effect(*args, **kwargs):
            trace.append("send")
            return True

        async def finalize_side_effect(*args, **kwargs):
            trace.append("finalize")

        with (
            patch(
                "src.consumers.review_liked.idempotency.reserve_key",
                side_effect=reserve_side_effect,
            ),
            patch(
                "src.consumers.review_liked.throttle.is_throttled",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch(
                "src.consumers.review_liked._get_review_liked_template",
                new_callable=AsyncMock,
                return_value={
                    "subject_template": "Hi {{ first_name }}",
                    "body_template": "Body",
                },
            ),
            patch(
                "src.consumers.review_liked.auth_client.get_user",
                new_callable=AsyncMock,
                return_value={
                    "email": "u@example.com",
                    "first_name": "A",
                    "last_name": "B",
                },
            ),
            patch("src.consumers.review_liked.template_renderer.render", return_value=("subject", "body")),
            patch("src.consumers.review_liked.email.send_email", side_effect=send_side_effect),
            patch(
                "src.consumers.review_liked.idempotency.finalize_key",
                side_effect=finalize_side_effect,
            ) as mock_finalize,
            patch("src.consumers.review_liked.throttle.set_throttle", new_callable=AsyncMock),
        ):
            await _handle(_payload())

        assert trace == ["reserve", "send", "finalize"]
        assert mock_finalize.await_args.kwargs["status"] == "SENT"


class TestProcessMessage:
    async def test_sends_domain_errors_to_dlq(self):
        from src.consumers.review_liked import _process_message

        payload = _payload()
        with (
            patch(
                "src.consumers.review_liked._handle",
                new_callable=AsyncMock,
                side_effect=KeyError("review_id"),
            ),
            patch(
                "src.consumers.review_liked._publish_dlq",
                new_callable=AsyncMock,
            ) as mock_dlq,
        ):
            should_commit = await _process_message(payload, AsyncMock())

        assert should_commit is True
        assert "domain_error:KeyError" in mock_dlq.await_args.args[2]

    async def test_retries_then_sends_to_dlq(self):
        from sqlalchemy.exc import OperationalError

        from src.consumers.review_liked import _process_message

        payload = _payload()
        with (
            patch("src.consumers.review_liked.settings.consumer_max_retries", 2),
            patch(
                "src.consumers.review_liked.settings.consumer_retry_delay_seconds",
                0.0,
            ),
            patch(
                "src.consumers.review_liked._handle",
                new_callable=AsyncMock,
                side_effect=OperationalError("SELECT 1", {}, Exception("db down")),
            ) as mock_handle,
            patch(
                "src.consumers.review_liked._publish_dlq",
                new_callable=AsyncMock,
            ) as mock_dlq,
            patch("src.consumers.review_liked.asyncio.sleep", new_callable=AsyncMock),
        ):
            should_commit = await _process_message(payload, AsyncMock())

        assert should_commit is True
        assert mock_handle.await_count == 2
        assert "retry_exhausted:OperationalError" in mock_dlq.await_args.args[2]
