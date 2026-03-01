from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.paginators import PaginationParams
from src.api.v1.responses import (
    GET_LOGS_RESPONSES,
    GET_ME_RESPONSES,
    GET_USER_ROLES_RESPONSES,
    LOGIN_CHANGE_RESPONSES,
    PASSWORD_CHANGE_RESPONSES,
)
from src.core.jwt import auth_dep
from src.models.log import Log
from src.models.role import Role
from src.models.user import User
from src.schemas.logs import LogResponse
from src.schemas.roles import RoleResponse
from src.schemas.users import (
    UserLoginChangeRequest,
    UserPasswordChangeRequest,
    UserResponse,
)
from src.services.roles import RoleService, get_role_service
from src.services.users import UserAlreadyExistsError, UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse, responses=GET_ME_RESPONSES)
async def get_current_user(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    await auth.jwt_required()
    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
    user: User | None = await user_service.get_user_by_id(user_id)
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
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await auth.fresh_jwt_required()

    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
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
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await auth.fresh_jwt_required()

    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
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
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> list[LogResponse]:
    await auth.jwt_required()

    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
    logs: list[Log] = await user_service.get_user_logs(
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
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    role_service: Annotated[RoleService, Depends(get_role_service)],
) -> list[RoleResponse]:
    await auth.jwt_required()

    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
    roles: list[Role] = await role_service.get_roles_by_user_id(user_id)
    return [RoleResponse(id=role.id, name=role.name) for role in roles]
