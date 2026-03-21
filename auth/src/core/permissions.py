from enum import StrEnum


class PermissionName(StrEnum):
    """Canonical permission identifiers used by RBAC checks."""

    PERMISSIONS_READ = "permissions:read"
    PERMISSIONS_ASSIGN = "permissions:assign"
    ROLES_READ = "roles:read"
    ROLES_CREATE = "roles:create"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    ROLES_ASSIGN = "roles:assign"
    CONTENT_READ = "content:read"
    CONTENT_CREATE = "content:create"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"
