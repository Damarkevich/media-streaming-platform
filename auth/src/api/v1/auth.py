from http import HTTPStatus
from typing import Annotated, Mapping
from uuid import UUID

from async_fastapi_jwt_auth import AuthJWT  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.v1.responses import (
    JWT_ACCESS_REQUIRED_RESPONSES,
    JWT_REFRESH_REQUIRED_RESPONSES,
    LOGIN_RESPONSES,
    SIGNUP_RESPONSES,
)
from src.core.jwt import auth_dep
from src.core.limiter import limiter
from src.models.log import LogType
from src.schemas.tokens import TokenResponse
from src.schemas.users import (
    UserCreate,
    UserLogin,
    UserResponse,
)
from src.services.roles import RoleService, get_role_service
from src.services.tokens import TokenService, get_token_service
from src.services.users import UserAlreadyExistsError, UserService, get_user_service

router = APIRouter(redirect_slashes=False)


def _extract_jti(payload: Mapping[str, object] | None) -> str:
    """Extract token JTI from a raw JWT payload."""
    if payload is None:
        return ""
    return str(payload.get("jti", ""))


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=HTTPStatus.CREATED,
    responses=SIGNUP_RESPONSES,
)
@limiter.limit("5/minute")
async def create_user(
    user_create: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
    request: Request,
) -> UserResponse:
    """Register a new user account and return its public projection."""
    user_dto = user_create.model_dump()
    try:
        user = await user_service.create_user(**user_dto)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="User with this email already exists",
        ) from exc
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, responses=LOGIN_RESPONSES)
@limiter.limit("5/minute")
async def login(
    user_login: UserLogin,
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    roles_service: Annotated[RoleService, Depends(get_role_service)],
    request: Request,
) -> TokenResponse:
    """Authenticate credentials and issue a new access/refresh token pair."""
    user_dto: dict[str, str] = user_login.model_dump()
    user = await user_service.authenticate_user(**user_dto)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid email or password",
        )
    roles = await roles_service.get_roles_by_user_id(user.id)
    roles_names: list[str] = [role.name for role in roles]
    access_token, refresh_token = await token_service.issue_tokens(
        user.id, roles_names, fresh=True
    )
    await user_service.log_user_action(user, LogType.LOGIN)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses=JWT_REFRESH_REQUIRED_RESPONSES,
)
async def refresh_token(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    roles_service: Annotated[RoleService, Depends(get_role_service)],
) -> TokenResponse:
    """Rotate tokens using a valid refresh token and return a new pair."""
    await auth.jwt_refresh_token_required()

    user_id: UUID = UUID(str(await auth.get_jwt_subject()))
    roles = await roles_service.get_roles_by_user_id(user_id)
    roles_names: list[str] = [role.name for role in roles]
    new_access_token, new_refresh_token = await token_service.issue_tokens(
        user_id, roles_names, fresh=False
    )

    old_refresh_jti = _extract_jti(await auth.get_raw_jwt())
    await token_service.add_refresh_to_blacklist(old_refresh_jti)

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.delete(
    "/access-revoke",
    status_code=HTTPStatus.NO_CONTENT,
    responses=JWT_ACCESS_REQUIRED_RESPONSES,
)
async def access_revoke(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> None:
    """Revoke the current access token."""
    await auth.jwt_required()

    old_access_jti = _extract_jti(await auth.get_raw_jwt())
    await token_service.add_access_to_blacklist(old_access_jti)


@router.delete(
    "/refresh-revoke",
    status_code=HTTPStatus.NO_CONTENT,
    responses=JWT_REFRESH_REQUIRED_RESPONSES,
)
async def refresh_revoke(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> None:
    """Revoke the current refresh token."""
    await auth.jwt_refresh_token_required()

    old_refresh_jti = _extract_jti(await auth.get_raw_jwt())
    await token_service.add_refresh_to_blacklist(old_refresh_jti)


@router.post("/api-login", response_model=UserResponse, responses=LOGIN_RESPONSES)
@limiter.limit("5/minute")
async def api_login(
    user_login: UserLogin,
    user_service: Annotated[UserService, Depends(get_user_service)],
    request: Request,
) -> UserResponse:
    """Authenticate credentials and issue a new access/refresh token pair."""
    user_dto: dict[str, str] = user_login.model_dump()
    user = await user_service.authenticate_user(**user_dto)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid email or password",
        )
    await user_service.log_user_action(user, LogType.API_LOGIN)
    return user
