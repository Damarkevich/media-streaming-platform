from pydantic import BaseModel


class ApiError(BaseModel):
    """Standard API error payload."""

    detail: str
