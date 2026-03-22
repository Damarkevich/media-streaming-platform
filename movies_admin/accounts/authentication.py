import http
from enum import StrEnum, auto

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()


class Roles(StrEnum):
    ADMIN = auto()
    SUBSCRIBER = auto()


def has_role(roles: list[Roles], required_role: Roles) -> bool:
    return required_role in roles


class MoviesAuthBackend(BaseBackend):
    """
    Custom Django authentication backend that validates credentials against an external API.

    This backend:
    - Authenticates users by sending credentials to a remote authentication service
    - Creates or updates local User objects based on API response data
    - Syncs user metadata (name, email, roles, status) with the local database
    - Supports role-based access control (admin/superuser assignment)
    """

    def authenticate(
        self, request, username: str | None = None, password: str | None = None
    ):
        url = settings.AUTH_API_LOGIN_URL
        payload = {"email": username, "password": password}
        response = httpx.post(url, json=payload)

        if response.status_code != http.HTTPStatus.OK:
            return None

        data = response.json()

        try:
            user, _ = User.objects.get_or_create(id=data["id"])
            user.email = data.get("email")
            user.first_name = data.get("first_name")
            user.last_name = data.get("last_name")
            user.is_staff = has_role(data.get("roles"), Roles.ADMIN)
            user.is_superuser = has_role(data.get("roles"), Roles.ADMIN)
            user.is_active = data.get("is_active")
            user.save()
        except Exception:
            return None

        return user

    def get_user(self, user_id: str | None = None):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
