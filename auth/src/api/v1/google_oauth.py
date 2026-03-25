from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.v1.responses import LOGIN_RESPONSES
from src.core.config import settings
from src.core.google_oauth import oauth
from src.core.limiter import limiter
from src.models.log import LogType
from src.schemas.tokens import TokenResponse
from src.services.google_oauth import (
    GoogleOAuthEmailError,
    GoogleOAuthError,
    GoogleOAuthService,
    GoogleUserDTO,
    get_google_oauth_service,
)
from src.services.roles import RoleService, get_role_service
from src.services.tokens import TokenService, get_token_service
from src.services.users import UserService, get_user_service

router = APIRouter(redirect_slashes=False)


@router.get("/google/login")
@limiter.limit("5/minute")
async def google_login(request: Request) -> Any:
    """Initiate Google OAuth2 login flow by redirecting to Google's auth endpoint."""
    redirect_uri: str = settings.google_redirect_uri
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=TokenResponse, responses=LOGIN_RESPONSES)
@limiter.limit("5/minute")
async def google_callback(
    google_oauth_service: Annotated[
        GoogleOAuthService, Depends(get_google_oauth_service)
    ],
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    roles_service: Annotated[RoleService, Depends(get_role_service)],
    request: Request,
) -> TokenResponse:
    """Handle Google OAuth2 callback, exchange code for jwt tokens, and return them."""

    # Extract email from Google OAuth token
    try:
        user_dto: GoogleUserDTO = await google_oauth_service.get_user_dto(request)
    except GoogleOAuthError as exc:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail="Google authentication failed",
        ) from exc
    except GoogleOAuthEmailError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Google account does not have a verified email",
        ) from exc

    # Check if user already exists, if not create a new one
    email: str = user_dto.email
    user = await user_service.get_user_by_email(email)
    if not user:
        user = await user_service.create_user(
            email=email,
            password=None,  # No password since it's OAuth
            first_name=user_dto.given_name,
            last_name=user_dto.family_name,
        )

    roles = await roles_service.get_roles_by_user_id(user.id)
    roles_names: list[str] = [role.name for role in roles]

    access_token, refresh_token = await token_service.issue_tokens(
        user.id, roles_names, fresh=True
    )
    await user_service.log_user_action(user, LogType.LOGIN)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
