from http import HTTPStatus
from typing import Annotated

from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException

from src.core.jwt import auth_dep
from src.schemas.entity import TokenResponse, UserCreate, UserLogin, UserResponse
from src.services.tokens import TokenService, get_token_service
from src.services.users import UserAlreadyExistsError, UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.post("/signup", response_model=UserResponse, status_code=HTTPStatus.CREATED)
async def create_user(
    user_create: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    user_dto = user_create.model_dump()
    try:
        return await user_service.create_user(**user_dto)
    except UserAlreadyExistsError as exc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail="User with this login already exists",
        ) from exc


@router.post("/login", response_model=TokenResponse)
async def login(
    user_login: UserLogin,
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> TokenResponse:
    user_dto = user_login.model_dump()
    user = await user_service.authenticate_user(**user_dto)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Invalid login or password",
        )
    access_token, refresh_token = await token_service.issue_tokens(str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> TokenResponse:
    await auth.jwt_refresh_token_required()

    user_id = await auth.get_jwt_subject()
    new_access_token, new_refresh_token = await token_service.issue_tokens(str(user_id))

    old_refresh_jti = str((await auth.get_raw_jwt()).get("jti", ""))
    await token_service.add_refresh_to_blacklist(old_refresh_jti)

    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.delete("/access-revoke", status_code=HTTPStatus.NO_CONTENT)
async def access_revoke(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> None:
    await auth.jwt_required()

    old_access_jti = str((await auth.get_raw_jwt()).get("jti", ""))
    await token_service.add_access_to_blacklist(old_access_jti)


@router.delete("/refresh-revoke", status_code=HTTPStatus.NO_CONTENT)
async def refresh_revoke(
    auth: Annotated[AuthJWT, Depends(auth_dep)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
) -> None:
    await auth.jwt_refresh_token_required()

    old_refresh_jti = str((await auth.get_raw_jwt()).get("jti", ""))
    await token_service.add_refresh_to_blacklist(old_refresh_jti)
