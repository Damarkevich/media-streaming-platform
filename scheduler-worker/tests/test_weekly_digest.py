"""Tests for src.jobs.weekly_digest."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


FAKE_TEMPLATE_ID = uuid.uuid4()
FAKE_FILMS = [{"id": "film-1", "title": "Great Movie", "imdb_rating": 9.0}]
FAKE_USER_IDS = ["user-aaa", "user-bbb", "user-ccc"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_row(value):
    """Return a mock that behaves like a SQLAlchemy Row."""
    row = MagicMock()
    row.__getitem__ = lambda self, i: value
    row.first.return_value = row
    return row


# ---------------------------------------------------------------------------
# run_weekly_digest
# ---------------------------------------------------------------------------


class TestRunWeeklyDigest:
    async def test_calls_run_on_success(self):
        from src.jobs.weekly_digest import run_weekly_digest

        with patch("src.jobs.weekly_digest._run", new_callable=AsyncMock) as mock_run:
            await run_weekly_digest()

        mock_run.assert_called_once()

    async def test_does_not_raise_when_run_fails(self):
        from src.jobs.weekly_digest import run_weekly_digest

        with patch(
            "src.jobs.weekly_digest._run",
            new_callable=AsyncMock,
            side_effect=RuntimeError("DB down"),
        ):
            await run_weekly_digest()  # must not propagate


# ---------------------------------------------------------------------------
# _get_template_id
# ---------------------------------------------------------------------------


class TestGetTemplateId:
    async def test_returns_uuid_when_row_exists(self):
        from src.jobs.weekly_digest import _get_template_id

        fake_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.first.return_value = (str(fake_id),)
        mock_execute = AsyncMock(return_value=mock_result)
        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.jobs.weekly_digest.async_session", return_value=mock_ctx):
            result = await _get_template_id()

        assert result == fake_id

    async def test_returns_none_when_no_row(self):
        from src.jobs.weekly_digest import _get_template_id

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.jobs.weekly_digest.async_session", return_value=mock_ctx):
            result = await _get_template_id()

        assert result is None


# ---------------------------------------------------------------------------
# _update_last_run
# ---------------------------------------------------------------------------


class TestUpdateLastRun:
    async def test_executes_update_and_commits(self):
        from src.jobs.weekly_digest import _update_last_run

        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.jobs.weekly_digest.async_session", return_value=mock_ctx):
            await _update_last_run()

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# _run — integration of all steps
# ---------------------------------------------------------------------------


class TestRun:
    def _patch_context(self, template_id, films, user_ids):
        """Return a list of patches needed for _run."""
        return [
            patch(
                "src.jobs.weekly_digest._get_template_id",
                new_callable=AsyncMock,
                return_value=template_id,
            ),
            patch(
                "src.jobs.weekly_digest.get_top_films",
                new_callable=AsyncMock,
                return_value=films,
            ),
            patch(
                "src.jobs.weekly_digest.get_all_user_ids",
                new_callable=AsyncMock,
                return_value=user_ids,
            ),
            patch(
                "src.jobs.weekly_digest._update_last_run",
                new_callable=AsyncMock,
            ),
        ]

    async def test_publishes_one_message_per_user(self):
        from src.jobs.weekly_digest import _run

        sent_messages: list[dict] = []

        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()

        async def fake_send(topic, key, value):
            sent_messages.append({"topic": topic, "key": key, "value": json.loads(value)})

        mock_producer.send = fake_send

        patches = self._patch_context(FAKE_TEMPLATE_ID, FAKE_FILMS, FAKE_USER_IDS)

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        assert len(sent_messages) == len(FAKE_USER_IDS)
        topics = {m["topic"] for m in sent_messages}
        assert topics == {"notifications.delivery"}

    async def test_message_contains_expected_fields(self):
        from src.jobs.weekly_digest import _run

        sent_messages: list[dict] = []
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()

        async def fake_send(topic, key, value):
            sent_messages.append(json.loads(value))

        mock_producer.send = fake_send
        user_ids = ["user-xyz"]

        patches = self._patch_context(FAKE_TEMPLATE_ID, FAKE_FILMS, user_ids)

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        msg = sent_messages[0]
        assert msg["user_id"] == "user-xyz"
        assert msg["template_id"] == str(FAKE_TEMPLATE_ID)
        assert msg["channel"] == "EMAIL"
        assert "films_list" in msg["template_variables"]
        assert "<ol>" in msg["template_variables"]["films_list"]
        assert "idempotency_key" in msg
        assert msg["idempotency_key"].startswith("weekly_digest:")
        assert ":user:user-xyz" in msg["idempotency_key"]

    async def test_aborts_when_no_template_id(self):
        from src.jobs.weekly_digest import _run

        mock_producer = AsyncMock()

        with (
            patch(
                "src.jobs.weekly_digest._get_template_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        mock_producer.start.assert_not_called()

    async def test_aborts_when_no_films(self):
        from src.jobs.weekly_digest import _run

        mock_producer = AsyncMock()

        with (
            patch(
                "src.jobs.weekly_digest._get_template_id",
                new_callable=AsyncMock,
                return_value=FAKE_TEMPLATE_ID,
            ),
            patch(
                "src.jobs.weekly_digest.get_top_films",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        mock_producer.start.assert_not_called()

    async def test_aborts_when_no_users(self):
        from src.jobs.weekly_digest import _run

        mock_producer = AsyncMock()

        with (
            patch(
                "src.jobs.weekly_digest._get_template_id",
                new_callable=AsyncMock,
                return_value=FAKE_TEMPLATE_ID,
            ),
            patch(
                "src.jobs.weekly_digest.get_top_films",
                new_callable=AsyncMock,
                return_value=FAKE_FILMS,
            ),
            patch(
                "src.jobs.weekly_digest.get_all_user_ids",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        mock_producer.start.assert_not_called()

    async def test_producer_is_stopped_even_if_send_fails(self):
        from src.jobs.weekly_digest import _run

        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.send = AsyncMock(side_effect=RuntimeError("Kafka error"))

        patches = self._patch_context(FAKE_TEMPLATE_ID, FAKE_FILMS, ["user-1"])

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            with pytest.raises(RuntimeError, match="Kafka error"):
                await _run()

        mock_producer.stop.assert_called_once()

    async def test_updates_last_run_after_publish(self):
        from src.jobs.weekly_digest import _run

        update_calls: list[bool] = []
        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()
        mock_producer.send = AsyncMock()

        async def fake_update():
            update_calls.append(True)

        patches = self._patch_context(FAKE_TEMPLATE_ID, FAKE_FILMS, FAKE_USER_IDS)

        with (
            patches[0],
            patches[1],
            patches[2],
            patch("src.jobs.weekly_digest._update_last_run", side_effect=fake_update),
            patch("src.jobs.weekly_digest.AIOKafkaProducer", return_value=mock_producer),
        ):
            await _run()

        assert update_calls == [True]
