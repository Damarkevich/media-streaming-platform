from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.models.user import User

POSTGRES_UNIQUE_VIOLATION_SQLSTATE = "23505"
LOGIN_FIELD_NAME = "login"


class UserAlreadyExistsError(Exception):
    """Raised when a user cannot be created because the login is already taken."""


def _is_login_unique_violation(exc: IntegrityError) -> bool:
    """Check whether an IntegrityError is a unique violation for the login field.

    This helper is intentionally conservative: it returns True only when the
    underlying database error looks like a Postgres unique-constraint violation
    and the constraint/message indicates it relates to the login.

    Args:
        exc: SQLAlchemy IntegrityError raised during commit.

    Returns:
        True if the error most likely represents a duplicate login.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate != POSTGRES_UNIQUE_VIOLATION_SQLSTATE:
        return False

    constraint = getattr(orig, "constraint_name", None)
    if isinstance(constraint, str) and LOGIN_FIELD_NAME in constraint.lower():
        return True

    return LOGIN_FIELD_NAME in str(orig).lower()


class UserService:
    """User-related application service.

    This layer encapsulates database operations and translates low-level DB
    exceptions into domain-level errors that API handlers can map to HTTP.
    """

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.
        """
        self.db = db

    async def create_user(
        self,
        login: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> User:
        """Create a new user.

        Args:
            login: Unique login identifier.
            password: Raw password. It is hashed by the User model.
            first_name: User first name.
            last_name: User last name.

        Returns:
            The persisted User ORM instance.

        Raises:
            UserAlreadyExistsError: If a user with the same login already exists.
            IntegrityError: For other database integrity errors.
        """
        user = User(
            login=login,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if _is_login_unique_violation(exc):
                raise UserAlreadyExistsError from exc
            raise
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: str, new_password: str) -> bool:
        """Change a user's password.

        Args:
            user_id: The UUID of the user as a string.
            new_password: The new raw password to set.

        Returns:
            True if a user row was updated, otherwise False.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(password=User.hash_password(new_password))
            .returning(User)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().one_or_none()
        await self.db.commit()
        return user is not None

    async def change_login(self, user_id: str, new_login: str) -> bool:
        """Change a user's login.

        Args:
            user_id: The UUID of the user as a string.
            new_login: The new login to set.

        Returns:
            True if a user row was updated, otherwise False.

        Raises:
            UserAlreadyExistsError: If another user with the new login already exists.
            IntegrityError: For other database integrity errors.
        """
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(login=new_login)
            .returning(User)
        )
        try:
            result = await self.db.execute(stmt)
            user = result.scalars().one_or_none()
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if _is_login_unique_violation(exc):
                raise UserAlreadyExistsError from exc
            raise
        return user is not None

    async def authenticate_user(self, login: str, password: str) -> User | None:
        """Authenticate a user by login and password.

        Args:
            login: User login.
            password: Raw password to verify.

        Returns:
            The authenticated User instance if credentials are valid, else None.
        """
        result = await self.db.execute(select(User).where(User.login == login))
        user = result.scalars().one_or_none()
        if user and user.check_password(password):
            return user
        return None

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id: The UUID of the user as a string.

        Returns:
            The User instance if found, else None.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().one_or_none()


def get_user_service(db: Annotated[AsyncSession, Depends(get_session)]) -> UserService:
    """FastAPI dependency provider for UserService.

    Args:
        db: Injected request-scoped async session.

    Returns:
        UserService instance bound to the current session.
    """
    return UserService(db)
