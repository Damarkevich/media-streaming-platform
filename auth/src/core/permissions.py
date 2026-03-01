from enum import StrEnum


class PermissionName(StrEnum):
    PERMISSIONS_READ = "permissions:read"
    PERMISSIONS_ASSIGN = "permissions:assign"
    ROLES_READ = "roles:read"
    ROLES_CREATE = "roles:create"
    ROLES_UPDATE = "roles:update"
    ROLES_DELETE = "roles:delete"
    ROLES_ASSIGN = "roles:assign"
