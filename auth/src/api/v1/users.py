from http import HTTPStatus
from typing import Annotated

from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException

from src.api.v1.responses import (
    GET_ME_RESPONSES,
    LOGIN_CHANGE_RESPONSES,
    PASSWORD_CHANGE_RESPONSES,
)
from src.core.jwt import auth_dep
from src.schemas.users import (
    UserLoginChangeRequest,
    UserPasswordChangeRequest,
    UserResponse,
)
from src.services.users import UserAlreadyExistsError, UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse, responses=GET_ME_RESPONSES)
async def get_current_user(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    await auth.jwt_required()
    user_id: str = str(await auth.get_jwt_subject())
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
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    await auth.jwt_required()

    user_id: str = str(await auth.get_jwt_subject())
    new_login: str = login_change_request.new_login
    try:
        is_updated = await user_service.change_login(user_id, new_login)
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
    await auth.jwt_required()

    user_id: str = str(await auth.get_jwt_subject())
    new_password: str = password_change_request.new_password
    is_updated = await user_service.change_password(user_id, new_password)
    if not is_updated:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="User not found",
        )
