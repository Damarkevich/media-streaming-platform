import http
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.token_models import TokenPayload
from src.core.token_validation import (
    decode_token,
    is_access_token_revoked,
    is_token_type_not_access,
)

bearer_scheme = HTTPBearer(auto_error=False)


async def authentication(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> TokenPayload:
    """Authenticate request and return decoded token payload."""
    if not credentials:
        raise HTTPException(
            status_code=http.HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Authorization credentials were not provided.",
        )
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=http.HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
            detail="Only Bearer tokens are accepted.",
        )

    decoded_token = decode_token(credentials.credentials)
    if not decoded_token:
        raise HTTPException(
            status_code=http.HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            detail="Invalid or expired token.",
        )
    if await is_token_type_not_access(decoded_token):
        raise HTTPException(
            status_code=http.HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            detail="Only access tokens are allowed.",
        )
    if await is_access_token_revoked(decoded_token):
        raise HTTPException(
            status_code=http.HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            detail="Token has been revoked.",
        )

    return decoded_token
