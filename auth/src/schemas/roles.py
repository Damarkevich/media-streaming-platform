from uuid import UUID

from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: UUID
    name: str


class RoleCreate(BaseModel):
    name: str


class RoleUpdate(BaseModel):
    name: str
