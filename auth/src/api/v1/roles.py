from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import UUID4

from src.api.v1.paginators import PaginationParams
from src.api.v1.responses import (
    ASSIGN_ROLE_TO_USER_RESPONSES,
    CREATE_ROLE_RESPONSES,
    DELETE_ROLE_RESPONSES,
    GET_ROLE_BY_ID_RESPONSES,
    GET_ROLE_PERMISSIONS_RESPONSES,
    GET_ROLES_RESPONSES,
    REMOVE_ROLE_FROM_USER_RESPONSES,
    UPDATE_ROLE_RESPONSES,
)
from src.models.role import PermissionName, Role
from src.schemas.permissions import PermissionResponse
from src.schemas.roles import (
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from src.services.permission_check import require_permission
from src.services.permissions import PermissionService, get_permission_service
from src.services.roles import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    RoleService,
    UserNotFoundError,
    get_role_service,
)

router = APIRouter(redirect_slashes=False)


@router.get(
    "",
    response_model=list[RoleResponse],
    responses=GET_ROLES_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_READ))],
)
async def get_roles(
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> list[RoleResponse]:
    roles: list[Role] = await role_service.get_roles(
        pagination.page_size, pagination.page_number
    )
    return [RoleResponse(id=role.id, name=role.name) for role in roles]


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    responses=GET_ROLE_BY_ID_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_READ))],
)
async def get_role_by_id(
    role_id: Annotated[UUID4, Path(description="The ID of the role to retrieve")],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleResponse:
    role: Role | None = await role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Role not found",
        )
    return RoleResponse(id=role.id, name=role.name)


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    response_model=RoleResponse,
    responses=CREATE_ROLE_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_CREATE))],
)
async def create_role(
    role_create: RoleCreate,
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> RoleResponse:
    try:
        role: Role = await role_service.create_role(role_create.name)
    except RoleAlreadyExistsError as exc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=str(exc),
        )
    return RoleResponse(id=role.id, name=role.name)


@router.patch(
    "/{role_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=UPDATE_ROLE_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_UPDATE))],
)
async def update_role(
    role_id: Annotated[UUID4, Path(description="The ID of the role to update")],
    role_update: RoleUpdate,
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> None:
    try:
        is_updated: bool = await role_service.update_role(role_id, role_update.name)
    except RoleAlreadyExistsError as exc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=str(exc),
        )
    if not is_updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Role not found",
        )


@router.delete(
    "/{role_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=DELETE_ROLE_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_DELETE))],
)
async def delete_role(
    role_id: Annotated[UUID4, Path(description="The ID of the role to delete")],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> None:
    is_deleted: bool = await role_service.delete_role(role_id)
    if not is_deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Role not found",
        )


@router.get(
    "/{role_id}/permissions",
    response_model=list[PermissionResponse],
    responses=GET_ROLE_PERMISSIONS_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.PERMISSIONS_READ))],
)
async def get_permissions_by_role_id(
    role_id: Annotated[
        UUID4, Path(description="The ID of the role to get permissions for")
    ],
    permission_service: Annotated[PermissionService, Depends(get_permission_service)],
) -> list[PermissionResponse]:
    permissions = await permission_service.get_permissions_by_role_id(role_id)
    return [
        PermissionResponse(id=permission.id, name=permission.name)
        for permission in permissions
    ]


@router.put(
    "/{role_id}/users/{user_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=ASSIGN_ROLE_TO_USER_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_ASSIGN))],
)
async def assign_role_to_user_by_path(
    role_id: Annotated[UUID4, Path(description="The ID of the role")],
    user_id: Annotated[UUID4, Path(description="The ID of the user")],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> None:
    try:
        await role_service.assign_role_to_user(user_id, role_id)
    except (RoleNotFoundError, UserNotFoundError) as exc:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc


@router.delete(
    "/{role_id}/users/{user_id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses=REMOVE_ROLE_FROM_USER_RESPONSES,
    dependencies=[Depends(require_permission(PermissionName.ROLES_ASSIGN))],
)
async def remove_role_from_user_by_path(
    role_id: Annotated[UUID4, Path(description="The ID of the role")],
    user_id: Annotated[UUID4, Path(description="The ID of the user")],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> None:
    try:
        await role_service.remove_role_from_user(user_id, role_id)
    except (RoleNotFoundError, UserNotFoundError) as exc:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(exc)) from exc
