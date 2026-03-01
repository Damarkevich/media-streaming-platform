from http import HTTPStatus
from typing import TypedDict

from src.schemas.errors import ApiError


class ResponseSpec(TypedDict, total=False):
    model: type
    description: str


OpenAPIResponses = dict[HTTPStatus, ResponseSpec]

SIGNUP_RESPONSES: OpenAPIResponses = {
    HTTPStatus.CONFLICT: {
        "model": ApiError,
        "description": "User with this login already exists",
    },
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "description": "Validation error",
    },
}

LOGIN_RESPONSES: OpenAPIResponses = {
    HTTPStatus.UNAUTHORIZED: {
        "model": ApiError,
        "description": "Invalid login or password",
    },
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "description": "Validation error",
    },
}

JWT_ACCESS_REQUIRED_RESPONSES: OpenAPIResponses = {
    HTTPStatus.UNAUTHORIZED: {
        "model": ApiError,
        "description": "Authentication required, token invalid, or token revoked",
    },
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "description": "Wrong token type or token validation error",
    },
}

JWT_REFRESH_REQUIRED_RESPONSES: OpenAPIResponses = {
    HTTPStatus.UNAUTHORIZED: {
        "model": ApiError,
        "description": "Authentication required, token invalid, or token revoked",
    },
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "description": "Wrong token type or token validation error",
    },
}

GET_ME_RESPONSES: OpenAPIResponses = {
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

LOGIN_CHANGE_RESPONSES: OpenAPIResponses = {
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

PASSWORD_CHANGE_RESPONSES: OpenAPIResponses = {
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

GET_LOGS_RESPONSES: OpenAPIResponses = {
    HTTPStatus.UNAUTHORIZED: {
        "model": ApiError,
        "description": "Authentication required, token invalid, or token revoked",
    },
    HTTPStatus.UNPROCESSABLE_ENTITY: {
        "description": "Wrong token type or token validation error",
    },
}
