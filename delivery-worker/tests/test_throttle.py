"""Tests for src.services.throttle."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestIsThrottled:
    async def test_returns_true_when_key_exists(self):
        from src.services.throttle import is_throttled

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        with patch("src.services.throttle.get_redis", return_value=mock_redis):
            result = await is_throttled("user-123")

        assert result is True
        mock_redis.exists.assert_called_once_with("notif:review_liked:user-123")

    async def test_returns_false_when_key_missing(self):
        from src.services.throttle import is_throttled

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        with patch("src.services.throttle.get_redis", return_value=mock_redis):
            result = await is_throttled("user-456")

        assert result is False

    async def test_key_format_uses_prefix(self):
        from src.services.throttle import THROTTLE_KEY_PREFIX, is_throttled

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        author_id = "abc-def"

        with patch("src.services.throttle.get_redis", return_value=mock_redis):
            await is_throttled(author_id)

        mock_redis.exists.assert_called_once_with(f"{THROTTLE_KEY_PREFIX}:{author_id}")


class TestSetThrottle:
    async def test_sets_key_with_ttl(self):
        from src.services.throttle import set_throttle

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("src.services.throttle.get_redis", return_value=mock_redis):
            await set_throttle("user-789")

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "notif:review_liked:user-789"
        assert call_args[0][1] == "1"
        # TTL must be positive
        assert call_args[1]["ex"] > 0

    async def test_ttl_is_86400_by_default(self):
        from src.services.throttle import set_throttle

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("src.services.throttle.get_redis", return_value=mock_redis):
            await set_throttle("user-000")

        call_args = mock_redis.set.call_args
        from src.core.config import settings
        assert call_args[1]["ex"] == settings.review_liked_throttle_ttl
