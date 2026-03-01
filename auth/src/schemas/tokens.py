from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT pair returned by authentication endpoints."""

    access_token: str
    refresh_token: str
