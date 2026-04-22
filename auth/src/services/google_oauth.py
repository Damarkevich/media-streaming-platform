import logging
from typing import Annotated, Any

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import Depends, Request
from pydantic import BaseModel, EmailStr

from src.core.google_oauth import get_google_oauth_client

logger = logging.getLogger(__name__)


class GoogleUserDTO(BaseModel):
    """
    Data Transfer Object (DTO) for user info returned by Google OAuth.

    Attributes:
        email: Email address of the user.
        email_verified: Whether the email is verified by Google.
        given_name: User's given (first) name.
        family_name: User's family (last) name.
    """

    email: EmailStr
    email_verified: bool
    given_name: str
    family_name: str


class GoogleOAuthError(Exception):
    """Raised when Google OAuth authentication fails."""


class GoogleOAuthEmailError(Exception):
    """Raised when Google OAuth email is missing or not verified."""


class GoogleOAuthService:
    """
    Service for handling Google OAuth authentication.

    Provides methods to extract and validate user info from Google OAuth tokens.
    """

    def __init__(self, oauth: OAuth) -> None:
        """
        Args:
            oauth: An initialized Authlib OAuth client.
        """
        self.oauth = oauth

    async def get_user_dto(self, request: Request) -> GoogleUserDTO:
        """
        Extract user information from Google OAuth token and return as DTO.

        Args:
            request: FastAPI request object.

        Returns:
            GoogleUserDTO: Parsed and validated user info from Google.

        Raises:
            GoogleOAuthError: If OAuth flow fails.
            GoogleOAuthEmailError: If email is missing or not verified.
        """
        try:
            token: dict[str, Any] = await self.oauth.google.authorize_access_token(
                request
            )
            user_info: dict[str, Any] = await self.oauth.google.parse_id_token(
                request, token
            )
        except OAuthError as exc:
            logger.error("Google OAuth authentication failed: %s", exc, exc_info=True)
            msg = "Google authentication failed"
            raise GoogleOAuthError(msg) from exc
        except Exception as exc:
            logger.error("Unexpected error during Google OAuth: %s", exc, exc_info=True)
            msg = "Unexpected error during Google authentication"
            raise GoogleOAuthError(msg) from exc

        try:
            dto = GoogleUserDTO(**user_info)
        except Exception as exc:
            logger.error("Failed to parse Google user info: %s", exc, exc_info=True)
            msg = "Invalid user info structure from Google"
            raise GoogleOAuthError(msg) from exc

        if not dto.email or not dto.email_verified:
            logger.warning(
                "Google account missing or unverified email: email=%r, verified=%r",
                dto.email,
                dto.email_verified,
            )
            msg = "Google account does not have a verified email"
            raise GoogleOAuthEmailError(msg)
        return dto


def get_google_oauth_service(
    oauth: Annotated[OAuth, Depends(get_google_oauth_client)],
) -> GoogleOAuthService:
    """Factory for GoogleOAuthService."""
    return GoogleOAuthService(oauth)
