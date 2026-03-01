from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.paginators import PaginationParams
from src.api.v1.responses import (
    GET_HAS_PERMISSION_RESPONSES,
    GET_LOGS_RESPONSES,
    GET_ME_RESPONSES,
    GET_USER_ROLES_RESPONSES,
    LOGIN_CHANGE_RESPONSES,
    PASSWORD_CHANGE_RESPONSES,
)
from src.core.permissions import PermissionName
from src.schemas.logs import LogResponse
from src.schemas.roles import RoleResponse
from src.schemas.users import (
    UserLoginChangeRequest,
    UserPasswordChangeRequest,
    UserPermissionCheckResponse,
    UserResponse,
)
from src.services.authorization import (
    get_authenticated_user_id,
    get_fresh_authenticated_user_id,
)
from src.services.permission_check import (
    PermissionCheckService,
    get_permission_check_service,
)
from src.services.roles import RoleService, get_role_service
from src.services.users import UserAlreadyExistsError, UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse, responses=GET_ME_RESPONSES)
async def get_current_user(
    user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User not found",
        )
    return user


@router.patch(
    "/me/login",
    status_code=HTTPStatus.NO_CONTENT,
    responses=LOGIN_CHANGE_RESPONSES,
)
async def change_login(
    login_change_request: UserLoginChangeRequest,
    user_id: Annotated[UUID, Depends(get_fresh_authenticated_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    new_login: str = login_change_request.new_login
    try:
        is_updated: bool = await user_service.change_login(user_id, new_login)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="User with this login already exists",
        ) from exc
    if not is_updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User not found",
        )


@router.patch(
    "/me/password",
    status_code=HTTPStatus.NO_CONTENT,
    responses=PASSWORD_CHANGE_RESPONSES,
)
async def change_password(
    password_change_request: UserPasswordChangeRequest,
    user_id: Annotated[UUID, Depends(get_fresh_authenticated_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    new_password: str = password_change_request.new_password
    is_updated: bool = await user_service.change_password(user_id, new_password)
    if not is_updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User not found",
        )


@router.get("/me/logs", response_model=list[LogResponse], responses=GET_LOGS_RESPONSES)
async def get_user_logs(
    pagination: Annotated[PaginationParams, Depends(PaginationParams)],
    user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> list[LogResponse]:
    logs = await user_service.get_user_logs(
        user_id, pagination.page_size, pagination.page_number
    )
    return [
        LogResponse(log_type=log.log_type, created_at=log.created_at) for log in logs
    ]


@router.get(
    "/me/roles",
    response_model=list[RoleResponse],
    responses=GET_USER_ROLES_RESPONSES,
)
async def get_user_roles(
    user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> list[RoleResponse]:
    roles = await role_service.get_roles_by_user_id(user_id)
    return [RoleResponse(id=role.id, name=role.name) for role in roles]


@router.get(
    "/me/has_permission/{permission_name}",
    response_model=UserPermissionCheckResponse,
    responses=GET_HAS_PERMISSION_RESPONSES,
)
async def check_user_permission(
    permission_name: PermissionName,
    user_id: Annotated[UUID, Depends(get_authenticated_user_id)],
    permission_check_service: Annotated[
        PermissionCheckService, Depends(get_permission_check_service)
    ],
) -> UserPermissionCheckResponse:
    has_perm = await permission_check_service.has_permission(user_id, permission_name)
    return UserPermissionCheckResponse(has_permission=has_perm)
