"""Tests for src.jobs.campaign_fanout."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch


class TestRunQueuedCampaigns:
    async def test_starts_and_stops_producer(self):
        from src.jobs.campaign_fanout import run_queued_campaigns

        mock_producer = AsyncMock()
        mock_producer.start = AsyncMock()
        mock_producer.stop = AsyncMock()

        with (
            patch("src.jobs.campaign_fanout.AIOKafkaProducer", return_value=mock_producer),
            patch(
                "src.jobs.campaign_fanout._process_one_campaign",
                new_callable=AsyncMock,
                side_effect=[True, False],
            ),
        ):
            await run_queued_campaigns()

        mock_producer.start.assert_called_once()
        mock_producer.stop.assert_called_once()


class TestProcessOneCampaign:
    async def test_returns_false_when_no_queued_campaign(self):
        from src.jobs.campaign_fanout import _process_one_campaign

        mock_producer = AsyncMock()
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.jobs.campaign_fanout.async_session", return_value=mock_ctx),
            patch(
                "src.jobs.campaign_fanout._claim_next_queued_campaign",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await _process_one_campaign(mock_producer)

        assert result is False
        mock_session.rollback.assert_called_once()

    async def test_processes_campaign_and_commits(self):
        from src.jobs.campaign_fanout import _process_one_campaign

        campaign_id = uuid.uuid4()
        template_id = uuid.uuid4()

        mock_producer = AsyncMock()
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.jobs.campaign_fanout.async_session", return_value=mock_ctx),
            patch(
                "src.jobs.campaign_fanout._claim_next_queued_campaign",
                new_callable=AsyncMock,
                return_value={
                    "id": campaign_id,
                    "template_id": template_id,
                    "template_variables": {"x": 1},
                },
            ),
            patch(
                "src.jobs.campaign_fanout.get_all_user_ids",
                new_callable=AsyncMock,
                return_value=["user-1", "user-2"],
            ),
            patch(
                "src.jobs.campaign_fanout._publish_campaign_messages",
                new_callable=AsyncMock,
            ) as mock_publish,
            patch(
                "src.jobs.campaign_fanout._mark_campaign_done",
                new_callable=AsyncMock,
            ) as mock_mark_done,
        ):
            result = await _process_one_campaign(mock_producer)

        assert result is True
        mock_publish.assert_called_once()
        mock_mark_done.assert_called_once_with(mock_session, campaign_id)
        mock_session.commit.assert_called_once()

    async def test_rolls_back_and_returns_false_on_error(self):
        from src.jobs.campaign_fanout import _process_one_campaign

        campaign_id = uuid.uuid4()
        template_id = uuid.uuid4()

        mock_producer = AsyncMock()
        mock_session = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.jobs.campaign_fanout.async_session", return_value=mock_ctx),
            patch(
                "src.jobs.campaign_fanout._claim_next_queued_campaign",
                new_callable=AsyncMock,
                return_value={
                    "id": campaign_id,
                    "template_id": template_id,
                    "template_variables": {},
                },
            ),
            patch(
                "src.jobs.campaign_fanout.get_all_user_ids",
                new_callable=AsyncMock,
                side_effect=RuntimeError("auth unavailable"),
            ),
        ):
            result = await _process_one_campaign(mock_producer)

        assert result is False
        mock_session.rollback.assert_called_once()


class TestPublishCampaignMessages:
    async def test_message_contains_expected_fields(self):
        from src.jobs.campaign_fanout import _publish_campaign_messages

        campaign_id = uuid.uuid4()
        template_id = uuid.uuid4()

        sent_payloads: list[dict] = []

        mock_producer = AsyncMock()

        async def fake_send(topic, key, value):
            import json

            sent_payloads.append(json.loads(value))
            assert topic == "notifications.delivery"
            assert key.decode().startswith(f"campaign:{campaign_id}:user:")

        mock_producer.send = fake_send

        await _publish_campaign_messages(
            producer=mock_producer,
            campaign_id=campaign_id,
            template_id=template_id,
            template_variables={"greeting": "hello"},
            user_ids=["u-1"],
        )

        msg = sent_payloads[0]
        assert msg["campaign_id"] == str(campaign_id)
        assert msg["template_id"] == str(template_id)
        assert msg["user_id"] == "u-1"
        assert msg["channel"] == "EMAIL"
        assert msg["template_variables"] == {"greeting": "hello"}
        assert msg["idempotency_key"] == f"campaign:{campaign_id}:user:u-1"
