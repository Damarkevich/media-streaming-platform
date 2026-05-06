"""Tests for src.services.templates."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


class TestGetAllTemplates:
    async def test_returns_list(self):
        from src.services.templates import get_all_templates

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = ["t1", "t2"]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_all_templates(mock_session)

        assert result == ["t1", "t2"]

    async def test_returns_empty_list_when_none(self):
        from src.services.templates import get_all_templates

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_all_templates(mock_session)

        assert result == []


class TestGetTemplate:
    async def test_returns_template_when_found(self):
        from src.services.templates import get_template

        template_id = uuid.uuid4()
        mock_template = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_template)

        result = await get_template(mock_session, template_id)

        assert result is mock_template
        mock_session.get.assert_called_once()

    async def test_returns_none_when_not_found(self):
        from src.services.templates import get_template

        template_id = uuid.uuid4()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        result = await get_template(mock_session, template_id)

        assert result is None


class TestCreateTemplate:
    async def test_creates_and_returns_template(self):
        from src.schemas.templates import TemplateCreate
        from src.services.templates import create_template

        data = TemplateCreate(
            name="test",
            notification_type="MANUAL_CAMPAIGN",
            subject_template="Hello {{ name }}",
            body_template="<p>Body {{ name }}</p>",
        )
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        result = await create_template(mock_session, data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert result.name == "test"
        assert result.notification_type == "MANUAL_CAMPAIGN"


class TestUpdateTemplate:
    async def test_updates_fields(self):
        from src.models.template import NotificationTemplate
        from src.schemas.templates import TemplateUpdate
        from src.services.templates import update_template

        template = NotificationTemplate(
            name="old_name",
            notification_type="MANUAL_CAMPAIGN",
            subject_template="Old subject",
            body_template="Old body",
        )
        data = TemplateUpdate(name="new_name", subject_template="New subject")
        mock_session = AsyncMock()

        result = await update_template(mock_session, template, data)

        assert result.name == "new_name"
        assert result.subject_template == "New subject"
        # Unchanged field stays
        assert result.notification_type == "MANUAL_CAMPAIGN"

    async def test_ignores_none_fields(self):
        from src.models.template import NotificationTemplate
        from src.schemas.templates import TemplateUpdate
        from src.services.templates import update_template

        template = NotificationTemplate(
            name="original",
            notification_type="MANUAL_CAMPAIGN",
            subject_template="Subj",
            body_template="Body",
        )
        data = TemplateUpdate()  # all None
        mock_session = AsyncMock()

        await update_template(mock_session, template, data)

        assert template.name == "original"


class TestGetTemplateOr404:
    async def test_returns_template_when_exists(self):
        from src.services.templates import get_template_or_404

        template_id = uuid.uuid4()
        mock_template = MagicMock()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_template)

        result = await get_template_or_404(mock_session, template_id)

        assert result is mock_template

    async def test_raises_404_when_not_found(self):
        from src.services.templates import get_template_or_404

        template_id = uuid.uuid4()
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_template_or_404(mock_session, template_id)

        assert exc_info.value.status_code == 404
        assert "Template not found" in exc_info.value.detail
