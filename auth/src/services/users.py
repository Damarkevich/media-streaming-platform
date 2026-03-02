import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.models.log import Log, LogType
from src.models.user import User
from src.services.utils import is_field_unique_violation

logger = logging.getLogger(__name__)


class UserAlreadyExistsError(Exception):
    """Raised when a user cannot be created because the login is already taken."""


class UserService:
    """User-related application service.

    This layer encapsulates database operations and translates low-level DB
    exceptions into domain-level errors that API handlers can map to HTTP.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.

        Returns:
            None.
        """
        self.db = db

    async def create_user(
        self,
        login: str,
        password: str,
        first_name: str,
        last_name: str,
        is_superuser: bool = False,
    ) -> User:
        """Create a new user.

        Args:
            login: Unique login identifier.
            password: Raw password. It is hashed by the User model.
            first_name: User first name.
            last_name: User last name.
            is_superuser: Whether the user should bypass permission checks.

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
            is_superuser=is_superuser,
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            if is_field_unique_violation(exc, "login"):
                raise UserAlreadyExistsError from exc
            raise
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        """Change a user's password.

        Args:
            user_id: The UUID of the user.
            new_password: The new raw password to set.

        Returns:
            True if a user row was updated, otherwise False.

        Raises:
            SQLAlchemyError: Propagates database errors.
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

    async def change_login(self, user_id: UUID, new_login: str) -> bool:
        """Change a user's login.

        Args:
            user_id: The UUID of the user.
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
            if is_field_unique_violation(exc, "login"):
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

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(User).where(User.login == login))
        user = result.scalars().one_or_none()
        if user and user.check_password(password):
            return user
        return None

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Retrieve a user by their unique ID.

        Args:
            user_id: The UUID of the user.

        Returns:
            The User instance if found, else None.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().one_or_none()

    async def log_user_action(self, user: User, log_type: LogType) -> None:
        """Log a user action.

        Args:
            user: The User instance.
            log_type: The type of action to log.

        Notes:
            This operation is best-effort and should not break the main request
            flow. Any database error is rolled back and logged.

        Returns:
            None.
        """
        log_entry = Log(user_id=user.id, log_type=log_type)
        self.db.add(log_entry)
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            logger.warning(
                f"Failed to persist user action log for user_id={user.id} and log_type={log_type}"
            )

    async def get_user_logs(
        self,
        user_id: UUID,
        page_size: int,
        page_number: int,
    ) -> list[Log]:
        """Get a paginated list of logs for a given user.

        Args:
            user_id: The UUID of the user.
            page_size: The number of logs to return per page.
            page_number: The page number to return.

        Returns:
            A list of Log instances associated with the user ordered by creation time descending.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        offset = page_number * page_size
        result = await self.db.execute(
            select(Log)
            .where(Log.user_id == user_id)
            .offset(offset)
            .limit(page_size)
            .order_by(Log.created_at.desc())
        )
        return list(result.scalars().all())


def get_user_service(db: Annotated[AsyncSession, Depends(get_session)]) -> UserService:
    """FastAPI dependency provider for UserService.

    Args:
        db: Injected request-scoped async session.

    Returns:
        UserService instance bound to the current session.
    """
    return UserService(db)
