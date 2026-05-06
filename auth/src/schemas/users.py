from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from src.schemas.roles import RoleResponse
from src.schemas.validators import validate_strong_password


class UserCreate(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserResponse(BaseModel):
    """Public user profile returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    roles: list[RoleResponse]


class UserLogin(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class UserEmailChangeRequest(BaseModel):
    """Request schema for changing user email."""

    new_email: EmailStr


class UserPasswordChangeRequest(BaseModel):
    """Request schema for changing user password."""

    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserPermissionCheckResponse(BaseModel):
    """Response schema for permission-check endpoint."""

    has_permission: bool


class UserInternalResponse(BaseModel):
    """Minimal user profile for internal service-to-service enrichment."""

    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str


class UserInternalListResponse(BaseModel):
    """Paginated list of users for campaign fanout."""

    items: list[UserInternalResponse]
    page: int
    page_size: int
