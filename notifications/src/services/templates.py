import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.template import NotificationTemplate
from src.schemas.templates import TemplateCreate, TemplateUpdate


async def get_all_templates(session: AsyncSession) -> list[NotificationTemplate]:
    result = await session.execute(select(NotificationTemplate))
    return list(result.scalars().all())


async def get_template(
    session: AsyncSession, template_id: uuid.UUID
) -> NotificationTemplate | None:
    return await session.get(NotificationTemplate, template_id)


async def create_template(
    session: AsyncSession, data: TemplateCreate
) -> NotificationTemplate:
    template = NotificationTemplate(**data.model_dump())
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


async def update_template(
    session: AsyncSession,
    template: NotificationTemplate,
    data: TemplateUpdate,
) -> NotificationTemplate:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(template, field, value)
    await session.commit()
    await session.refresh(template)
    return template


async def delete_template(
    session: AsyncSession, template: NotificationTemplate
) -> None:
    await session.delete(template)
    await session.commit()


async def get_template_or_404(
    session: AsyncSession, template_id: uuid.UUID
) -> NotificationTemplate:
    template = await get_template(session, template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )
    return template
