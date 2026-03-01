from uuid import UUID

from pydantic import BaseModel


class RoleResponse(BaseModel):
    """Response schema for role projection."""

    id: UUID
    name: str


class RoleCreate(BaseModel):
    """Request schema for role creation."""

    name: str


class RoleUpdate(BaseModel):
    """Request schema for role rename operation."""

    name: str
