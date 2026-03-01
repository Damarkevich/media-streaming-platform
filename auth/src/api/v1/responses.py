from http import HTTPStatus
from typing import Any

from src.schemas.errors import ApiError

OpenAPIResponses = dict[int | str, dict[str, Any]]


def _normalize_responses(
    responses: dict[HTTPStatus, dict[str, Any]],
) -> OpenAPIResponses:
    return {int(status): spec for status, spec in responses.items()}


SIGNUP_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.CONFLICT: {
            "model": ApiError,
            "description": "User with this login already exists",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Validation error",
        },
    }
)

LOGIN_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Invalid login or password",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Validation error",
        },
    }
)

JWT_ACCESS_REQUIRED_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

JWT_REFRESH_REQUIRED_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

GET_ME_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "User not found",
        },
    }
)

LOGIN_CHANGE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, token revoked, or fresh access token required",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.CONFLICT: {
            "model": ApiError,
            "description": "User with this login already exists",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "User not found",
        },
    }
)

PASSWORD_CHANGE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, token revoked, or fresh access token required",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "User not found",
        },
    }
)

GET_LOGS_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

GET_USER_ROLES_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

GET_ROLES_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

GET_ROLE_BY_ID_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role not found",
        },
    }
)

CREATE_ROLE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Validation error",
        },
        HTTPStatus.CONFLICT: {
            "model": ApiError,
            "description": "Role with this name already exists",
        },
    }
)

UPDATE_ROLE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.CONFLICT: {
            "model": ApiError,
            "description": "Role with this name already exists",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role not found",
        },
    }
)

DELETE_ROLE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role not found",
        },
    }
)

GET_ROLE_PERMISSIONS_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

ASSIGN_ROLE_TO_USER_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role or user not found",
        },
    }
)

REMOVE_ROLE_FROM_USER_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role or user not found",
        },
    }
)

GET_PERMISSIONS_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Wrong token type or token validation error",
        },
    }
)

ASSIGN_PERMISSION_TO_ROLE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role or permission not found",
        },
    }
)

REMOVE_PERMISSION_FROM_ROLE_RESPONSES: OpenAPIResponses = _normalize_responses(
    {
        HTTPStatus.UNAUTHORIZED: {
            "model": ApiError,
            "description": "Authentication required, token invalid, or token revoked",
        },
        HTTPStatus.FORBIDDEN: {
            "model": ApiError,
            "description": "Insufficient permissions",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "Request validation error, wrong token type, or token validation error",
        },
        HTTPStatus.NOT_FOUND: {
            "model": ApiError,
            "description": "Role or permission not found",
        },
    }
)
