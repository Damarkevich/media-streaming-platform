from http import HTTPStatus
from typing import Annotated

from async_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException

from src.core.jwt import auth_dep
from src.schemas.entity import UserResponse
from src.services.users import UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.get("/me", response_model=UserResponse)
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
