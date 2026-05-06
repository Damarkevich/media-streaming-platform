"""Tests for src.main._load_cron."""

from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# _load_cron
# ---------------------------------------------------------------------------


class TestLoadCron:
    async def test_returns_cron_from_db_when_row_exists(self):
        from src.main import _load_cron

        mock_result = MagicMock()
        mock_result.first.return_value = ("0 10 * * 5",)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.main.async_session", return_value=mock_ctx):
            result = await _load_cron()

        assert result == "0 10 * * 5"

    async def test_falls_back_to_settings_when_no_row(self):
        from src.main import _load_cron

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.main.async_session", return_value=mock_ctx):
            result = await _load_cron()

        from src.core.config import settings
        assert result == settings.weekly_digest_cron

    async def test_falls_back_to_settings_on_db_exception(self):
        from src.main import _load_cron

        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=Exception("DB unreachable"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.main.async_session", return_value=mock_ctx):
            result = await _load_cron()

        from src.core.config import settings
        assert result == settings.weekly_digest_cron

    async def test_default_cron_is_five_parts(self):
        """Ensure default cron string has exactly 5 space-separated parts."""
        from src.core.config import settings

        parts = settings.weekly_digest_cron.split()
        assert len(parts) == 5

    async def test_returns_string(self):
        from src.main import _load_cron

        mock_result = MagicMock()
        mock_result.first.return_value = ("*/30 * * * *",)
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.main.async_session", return_value=mock_ctx):
            result = await _load_cron()

        assert isinstance(result, str)
        assert result == "*/30 * * * *"
