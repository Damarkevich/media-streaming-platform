"""Tests for src.services.campaigns."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestGetAllCampaigns:
    async def test_returns_list(self):
        from src.services.campaigns import get_all_campaigns

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["c1", "c2"]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_all_campaigns(mock_session)

        assert result == ["c1", "c2"]


class TestGetCampaign:
    async def test_returns_campaign_when_found(self):
        from src.services.campaigns import get_campaign

        campaign_id = uuid.uuid4()
        mock_campaign = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_campaign)

        result = await get_campaign(mock_session, campaign_id)

        assert result is mock_campaign

    async def test_returns_none_when_not_found(self):
        from src.services.campaigns import get_campaign

        campaign_id = uuid.uuid4()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        result = await get_campaign(mock_session, campaign_id)

        assert result is None


class TestCreateCampaign:
    async def test_creates_campaign_with_created_by(self):
        from src.schemas.campaigns import CampaignCreate
        from src.services.campaigns import create_campaign

        template_id = uuid.uuid4()
        user_id = uuid.uuid4()
        data = CampaignCreate(
            name="Test Campaign",
            template_id=template_id,
            template_variables={"title": "Top films"},
        )
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await create_campaign(mock_session, data, user_id)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert result.name == "Test Campaign"
        assert result.created_by == user_id


class TestMarkQueued:
    async def test_sets_status_to_queued(self):
        from src.services.campaigns import mark_queued

        mock_campaign = MagicMock()
        mock_campaign.status = "DRAFT"
        mock_session = AsyncMock()

        await mark_queued(mock_session, mock_campaign)

        assert mock_campaign.status == "QUEUED"
        assert mock_campaign.triggered_at is not None
        mock_session.commit.assert_called_once()

    async def test_raises_409_for_non_draft(self):
        from src.services.campaigns import mark_queued

        mock_campaign = MagicMock()
        mock_campaign.status = "QUEUED"
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await mark_queued(mock_session, mock_campaign)

        assert exc_info.value.status_code == 409

    async def test_raises_409_for_done_campaign(self):
        from src.services.campaigns import mark_queued

        mock_campaign = MagicMock()
        mock_campaign.status = "DONE"
        mock_session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await mark_queued(mock_session, mock_campaign)

        assert exc_info.value.status_code == 409
        assert "DONE" in exc_info.value.detail


class TestRunFanout:
    async def test_logs_error_when_campaign_not_found(self):
        from src.services.campaigns import run_fanout

        campaign_id = uuid.uuid4()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.campaigns.async_session", return_value=mock_ctx):
            # Should not raise — just log and return
            await run_fanout(campaign_id)

    async def test_marks_campaign_failed_on_exception(self):
        from src.models.campaign import Campaign
        from src.services.campaigns import run_fanout

        campaign_id = uuid.uuid4()
        mock_campaign = MagicMock(spec=Campaign)
        mock_campaign.id = campaign_id
        mock_campaign.status = "QUEUED"
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_campaign)
        mock_session.commit = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.campaigns.async_session", return_value=mock_ctx):
            with patch(
                "src.services.campaigns._fanout",
                side_effect=RuntimeError("kafka down"),
            ):
                await run_fanout(campaign_id)

        assert mock_campaign.status == "FAILED"
        mock_session.commit.assert_called()
