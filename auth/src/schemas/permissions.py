from uuid import UUID

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    """Response schema for permission projection."""

    id: UUID
    name: str
