import logging
from enum import StrEnum, auto

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

logger = logging.getLogger(__name__)

User = get_user_model()


class RoleName(StrEnum):
    ADMIN = auto()


def has_role(roles: list[dict[str, str]] | None, required_role: RoleName) -> bool:
    """Return True if the required role is present in the roles payload.

    Role names are compared case-insensitively. Missing or empty role data
    returns False.
    """
    if not roles:
        return False

    required_value = required_role.value.casefold()
    return any((role.get("name") or "").casefold() == required_value for role in roles)


class MoviesAuthBackend(BaseBackend):
    """
    Authenticate against the external auth service and sync a local Django user.

    On successful external authentication, the backend updates local user fields
    and stores a Django password hash so the default ModelBackend can be used as
    a fallback authentication path when needed.
    """

    def authenticate(
        self, request, username: str | None = None, password: str | None = None
    ):
        """Authenticate a user via external API and upsert the local user record.

        Returns:
            User: Authenticated local user object.
            None: If remote authentication fails or local sync raises an error.
        """
        url = settings.AUTH_API_LOGIN_URL
        payload = {"email": username, "password": password}

        try:
            response = httpx.post(url, json=payload, timeout=5.0)
            response.raise_for_status()
            logger.info(
                f"[MoviesAuthBackend] API request successful for user {username}"
            )
        except httpx.RequestError:
            logger.warning(
                f"[MoviesAuthBackend] API request failed for user {username}"
            )
            return None
        except httpx.HTTPStatusError:
            logger.warning(
                f"[MoviesAuthBackend] API request returned an error for user {username}"
            )
            return None

        data = response.json()

        try:
            user, _ = User.objects.update_or_create(
                id=data["id"],
                defaults={
                    "email": data.get("email"),
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "is_staff": has_role(data.get("roles", []), RoleName.ADMIN),
                    "is_active": data.get("is_active", True),
                },
            )

            # Save hashed password to use Django's authentication system as fallback
            user.set_password(password)
            user.save(update_fields=["password"])

        except Exception:
            logger.exception(
                f"[MoviesAuthBackend] Error creating/updating user {username}"
            )
            return None
        logger.info(
            f"[MoviesAuthBackend] User {username} authenticated successfully with ID {user.id}"
        )
        return user

    def get_user(self, user_id: str | None = None):
        """Return a local user by primary key or None if the user does not exist."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
