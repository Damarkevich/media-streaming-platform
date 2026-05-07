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
