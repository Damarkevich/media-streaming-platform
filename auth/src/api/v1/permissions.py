from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import UUID4

from src.api.v1.paginators import PaginationParams
from src.api.v1.responses import (
    ASSIGN_PERMISSION_TO_ROLE_RESPONSES,
    GET_PERMISSIONS_RESPONSES,
    REMOVE_PERMISSION_FROM_ROLE_RESPONSES,
)
from src.core.permissions import PermissionName
from src.schemas.permissions import PermissionResponse
from src.services.authorization import require_permission
from src.services.permissions import (
    PermissionNotFoundError,
    PermissionService,
    RoleNotFoundError,
    get_permission_service,
)

router = APIRouter(redirect_slashes=False)


@router.get(
    "",
    response_model=list[PermissionResponse],
    responses=GET_PERMISSIONS_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.PERMISSIONS_READ))],
)
async def get_permissions(
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> list[PermissionResponse]:
    permissions = await permission_service.get_permissions(
        pagination.page_size, pagination.page_number
    )
    return [
        PermissionResponse(id=permission.id, name=permission.name)
        for permission in permissions
    ]


@router.put(
    "/{permission_id}/roles/{role_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=ASSIGN_PERMISSION_TO_ROLE_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.PERMISSIONS_ASSIGN))],
)
async def assign_permission_to_role_by_path(
    permission_id: Annotated[
        UUID4, Path(description="The ID of the permission to assign")
    ],
    role_id: Annotated[UUID4, Path(description="The ID of the role")],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    try:
        await permission_service.assign_permission_to_role(role_id, permission_id)
    except (RoleNotFoundError, PermissionNotFoundError) as exc:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{permission_id}/roles/{role_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=REMOVE_PERMISSION_FROM_ROLE_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.PERMISSIONS_ASSIGN))],
)
async def remove_permission_from_role_by_path(
    permission_id: Annotated[
        UUID4, Path(description="The ID of the permission to remove")
    ],
    role_id: Annotated[UUID4, Path(description="The ID of the role")],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> None:
    try:
        await permission_service.remove_permission_from_role(role_id, permission_id)
    except (RoleNotFoundError, PermissionNotFoundError) as exc:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
