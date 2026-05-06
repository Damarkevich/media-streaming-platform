import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import require_admin
from src.db.postgres import get_session
from src.schemas.templates import TemplateCreate, TemplateResponse, TemplateUpdate
from src.services import templates as svc

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TemplateResponse]:
    return await svc.get_all_templates(session)  # type: ignore[return-value]


@router.post(
    "/",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: TemplateCreate,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateResponse:
    return await svc.create_template(session, data)  # type: ignore[return-value]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateResponse:
    return await svc.get_template_or_404(session, template_id)  # type: ignore[return-value]


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID,
    data: TemplateUpdate,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TemplateResponse:
    template = await svc.get_template_or_404(session, template_id)
    return await svc.update_template(session, template, data)  # type: ignore[return-value]


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: uuid.UUID,
    _: Annotated[None, Depends(require_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    template = await svc.get_template_or_404(session, template_id)
    await svc.delete_template(session, template)
