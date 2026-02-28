from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any("A" <= ch <= "Z" for ch in value):
            raise ValueError(
                "password must contain at least one uppercase English letter"
            )
        if not any("a" <= ch <= "z" for ch in value):
            raise ValueError(
                "password must contain at least one lowercase English letter"
            )
        if not any(ch.isdigit() for ch in value):
            raise ValueError("password must contain at least one digit")
        if not any(not ch.isalnum() for ch in value):
            raise ValueError("password must contain at least one special character")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str


class UserLogin(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
