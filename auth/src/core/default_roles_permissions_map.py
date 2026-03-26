from enum import StrEnum

from src.core.permissions import PermissionName


class DefaultRole(StrEnum):
    """Canonical role identifiers used for default role assignment."""

    ADMIN = "admin"
    SUBSCRIBER = "subscriber"


DEFAULT_ROLES_PERMISSIONS_MAP: dict[DefaultRole, list[PermissionName]] = {
    DefaultRole.ADMIN: [
        PermissionName.PERMISSIONS_READ,
        PermissionName.PERMISSIONS_ASSIGN,
        PermissionName.ROLES_READ,
        PermissionName.ROLES_CREATE,
        PermissionName.ROLES_UPDATE,
        PermissionName.ROLES_DELETE,
        PermissionName.ROLES_ASSIGN,
        PermissionName.CONTENT_READ,
        PermissionName.CONTENT_CREATE,
        PermissionName.CONTENT_UPDATE,
        PermissionName.CONTENT_DELETE,
    ],
    DefaultRole.SUBSCRIBER: [PermissionName.CONTENT_READ],
}
