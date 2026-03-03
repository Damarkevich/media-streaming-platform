import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.postgres import get_session
from src.models.role import Role, UserRole
from src.models.user import User
from src.services.permission_check import invalidate_user_permissions_cache
from src.services.redis import RedisClient, get_redis_client
from src.services.utils import is_field_unique_violation

logger = logging.getLogger(__name__)


class RoleAlreadyExistsError(Exception):
    """Raised when a role cannot be created because the name is already taken."""


class RoleNotFoundError(Exception):
    """Raised when the requested role does not exist."""


class UserNotFoundError(Exception):
    """Raised when the requested user does not exist."""


class RoleService:
    """Role-related application service.

    This layer encapsulates database operations and translates low-level DB
    exceptions into domain-level errors that API handlers can map to HTTP.
    """

    def __init__(self, db: AsyncSession, redis_client: RedisClient) -> None:
        """Initialize the service.

        Args:
            db: Request-scoped SQLAlchemy async session.
            redis_client: Injected Redis client wrapper.

        Returns:
            None.
        """
        self.db = db
        self.redis_client = redis_client

    async def create_role(self, name: str) -> Role:
        """Create a new role with the given name.

        Args:
            name: Name of the role to create.

        Returns:
            The created Role instance.

        Raises:
            RoleAlreadyExistsError: If a role with the same name already exists.
            SQLAlchemyError: For other database errors.
        """
        new_role = Role(name=name)
        self.db.add(new_role)
        try:
            await self.db.commit()
            await self.db.refresh(new_role)
            return new_role
        except IntegrityError as exc:
            await self.db.rollback()
            if is_field_unique_violation(exc, "name"):
                raise RoleAlreadyExistsError(
                    f"Role with name '{name}' already exists."
                ) from exc
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def update_role(self, role_id: UUID, new_name: str) -> bool:
        """Update the name of an existing role.

        Args:
            role_id: ID of the role to update.
            new_name: New name for the role.

        Returns:
            True if the role was updated, False if no such role exists.

        Raises:
            RoleAlreadyExistsError: If a role with the new name already exists.
            SQLAlchemyError: For other database errors.
        """
        stmt = (
            update(Role)
            .where(Role.id == role_id)
            .values(name=new_name)
            .execution_options(synchronize_session="fetch")
        )
        try:
            result = await self.db.execute(stmt)
            if (getattr(result, "rowcount", 0) or 0) == 0:
                return False
            await self.db.commit()
            return True
        except IntegrityError as exc:
            await self.db.rollback()
            if is_field_unique_violation(exc, "name"):
                raise RoleAlreadyExistsError(
                    f"Role with name '{new_name}' already exists."
                ) from exc
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def delete_role(self, role_id: UUID) -> bool:
        """Delete a role by ID.

        Args:
            role_id: ID of the role to delete.

        Returns:
            True if the role was deleted, False if no such role exists.

        Raises:
            SQLAlchemyError: If database operations fail.
        """
        user_ids_result = await self.db.execute(
            select(UserRole.user_id).where(UserRole.role_id == role_id)
        )
        affected_user_ids = list(user_ids_result.scalars().all())

        stmt = delete(Role).where(Role.id == role_id)
        result = await self.db.execute(stmt)
        if (getattr(result, "rowcount", 0) or 0) == 0:
            return False
        await self.db.commit()
        for user_id in affected_user_ids:
            await invalidate_user_permissions_cache(self.redis_client, user_id)
        return True

    async def get_roles(self, page_size: int, page_number: int) -> list[Role]:
        """Get a paginated list of roles.

        Args:
            page_size: The number of roles to return per page.
            page_number: The page number to return (0-based).

        Returns:
            A list of Role instances for the requested page.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """

        offset = page_number * page_size
        stmt = (
            select(Role)
            .offset(offset)
            .limit(page_size)
            .order_by(Role.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        """Retrieve a role by its unique ID.

        Args:
            role_id: The UUID of the role.

        Returns:
            The Role instance if found, else None.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(Role).where(Role.id == role_id))
        return result.scalars().one_or_none()

    async def get_roles_by_user_id(
        self,
        user_id: UUID,
    ) -> list[Role]:
        """Get a list of roles assigned to a specific user.

        Args:
            user_id: The UUID of the user.

        Returns:
            A list of Role instances assigned to the user.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        stmt = (
            select(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        """Assign a role to a user.

        Args:
            user_id: The UUID of the user.
            role_id: The UUID of the role.

        Returns:
            None.

        Raises:
            RoleNotFoundError: If role does not exist.
            UserNotFoundError: If user does not exist.
            SQLAlchemyError: If persistence fails.
        """
        if not await self._role_exists(role_id):
            raise RoleNotFoundError("Role not found")
        if not await self._user_exists(user_id):
            raise UserNotFoundError("User not found")

        if await self._user_role_exists(user_id=user_id, role_id=role_id):
            return

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        try:
            await self.db.commit()
            await invalidate_user_permissions_cache(self.redis_client, user_id)
        except IntegrityError:
            await self.db.rollback()
            if await self._user_role_exists(user_id=user_id, role_id=role_id):
                return
            raise
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        """Remove a role assignment from a user.

        Args:
            user_id: The UUID of the user.
            role_id: The UUID of the role.

        Returns:
            None.

        Raises:
            RoleNotFoundError: If role does not exist.
            UserNotFoundError: If user does not exist.
            SQLAlchemyError: If persistence fails.
        """
        if not await self._role_exists(role_id):
            raise RoleNotFoundError("Role not found")
        if not await self._user_exists(user_id):
            raise UserNotFoundError("User not found")

        stmt = delete(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
        try:
            result = await self.db.execute(stmt)
            if (getattr(result, "rowcount", 0) or 0) == 0:
                return
            await self.db.commit()
            await invalidate_user_permissions_cache(self.redis_client, user_id)
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def _role_exists(self, role_id: UUID) -> bool:
        """Return whether role with given ID exists.

        Args:
            role_id: Role identifier.

        Returns:
            True when role exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(Role.id).where(Role.id == role_id))
        return result.scalar_one_or_none() is not None

    async def _user_exists(self, user_id: UUID) -> bool:
        """Return whether user with given ID exists.

        Args:
            user_id: User identifier.

        Returns:
            True when user exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(select(User.id).where(User.id == user_id))
        return result.scalar_one_or_none() is not None

    async def _user_role_exists(self, user_id: UUID, role_id: UUID) -> bool:
        """Return whether user-role relation already exists.

        Args:
            user_id: User identifier.
            role_id: Role identifier.

        Returns:
            True when relation exists.

        Raises:
            SQLAlchemyError: Propagates database query errors.
        """
        result = await self.db.execute(
            select(UserRole)
            .where(UserRole.user_id == user_id, UserRole.role_id == role_id)
            .limit(1)
        )
        return result.scalars().one_or_none() is not None


def get_role_service(
    db: Annotated[AsyncSession, Depends(get_session)],
    redis_client: Annotated[RedisClient, Depends(get_redis_client)],
) -> RoleService:
    """FastAPI dependency provider for RoleService.

    Args:
        db: Injected request-scoped async session.
        redis_client: Injected Redis client wrapper.

    Returns:
        RoleService instance bound to the current session.
    """
    return RoleService(db=db, redis_client=redis_client)
