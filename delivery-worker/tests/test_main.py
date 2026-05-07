"""Tests for src.main shutdown behavior."""

from unittest.mock import AsyncMock, patch

import pytest


class TestMainShutdown:
    async def test_closes_clients_on_failure(self):
        from src.main import main

        with (
            patch(
                "src.main.run_delivery",
                new_callable=AsyncMock,
                side_effect=RuntimeError("consumer failed"),
            ),
            patch("src.main.run_review_liked", new_callable=AsyncMock),
            patch("src.main.close_http_client", new_callable=AsyncMock) as close_http,
            patch("src.main.close_redis", new_callable=AsyncMock) as close_redis,
            patch("src.main.close_brevo_client", new_callable=AsyncMock) as close_brevo,
        ):
            with pytest.raises(RuntimeError, match="consumer failed"):
                await main()

        close_http.assert_called_once()
        close_redis.assert_called_once()
        close_brevo.assert_called_once()
