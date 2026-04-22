import asyncio
from typing import Annotated

import typer
from sqlalchemy import select

from src.db.postgres import async_session
from src.models.role import Role, UserRole
from src.models.user import User
from src.schemas.validators import validate_strong_password
from src.services.users import UserAlreadyExistsError, UserService

AdminRoleName = "admin"


class AdminRoleNotFoundError(Exception):
    """Raised when the required admin role is not found in the system."""


app = typer.Typer(
    no_args_is_help=True,
    help="CLI utilities for the auth service.",
)


@app.callback()
def cli() -> None:
    """Auth service command-line interface."""


@app.command("create-superuser")
def create_superuser(
    email: Annotated[
        str,
        typer.Option(
            "--email",
            "-e",
            prompt=True,
            help="Superuser email.",
        ),
    ],
    password: Annotated[
        str,
        typer.Option(
            "--password",
            "-p",
            prompt=True,
            hide_input=True,
            confirmation_prompt=True,
            help="Superuser password.",
        ),
    ],
    first_name: Annotated[
        str,
        typer.Option("--first-name", "-f", help="Superuser first name."),
    ] = "Super",
    last_name: Annotated[
        str,
        typer.Option("--last-name", "-n", help="Superuser last name."),
    ] = "Admin",
) -> None:
    """Create a superuser account with unrestricted permissions."""

    async def _run() -> None:
        async with async_session() as db:
            user_service = UserService(db)
            user: User = await user_service.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_superuser=True,
            )

            result = await db.execute(select(Role).where(Role.name == AdminRoleName))
            role: Role | None = result.scalars().one_or_none()
            if not role:
                msg = f"Required role '{AdminRoleName}' not found in the system."
                raise AdminRoleNotFoundError(msg)

            db.add(UserRole(user_id=user.id, role_id=role.id))
            await db.commit()

    try:
        email = User.normalize_email(email)
        password = validate_strong_password(password)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    try:
        asyncio.run(_run())
    except UserAlreadyExistsError:
        typer.secho(
            f"User with email '{email}' already exists.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from None
    except AdminRoleNotFoundError:
        typer.secho(
            f"Required role '{AdminRoleName}' not found in the system.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from None
    typer.secho(
        f"Superuser '{email}' created successfully.",
        fg=typer.colors.GREEN,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
