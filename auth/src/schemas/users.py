from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.schemas.validators import validate_login, validate_strong_password


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)

    @field_validator("login")
    @classmethod
    def validate_login(cls, value: str) -> str:
        return validate_login(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_strong_password(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str


class UserLogin(BaseModel):
    login: str
    password: str


class UserLoginChangeRequest(BaseModel):
    new_login: str = Field(min_length=3, max_length=255)

    @field_validator("new_login")
    @classmethod
    def validate_new_login(cls, value: str) -> str:
        return validate_login(value)


class UserPasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_strong_password(value)
