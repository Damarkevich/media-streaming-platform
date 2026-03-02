import asyncio
from typing import Annotated

import typer

from src.db.postgres import async_session
from src.schemas.validators import validate_login, validate_strong_password
from src.services.users import UserAlreadyExistsError, UserService

app = typer.Typer(
    no_args_is_help=True,
    help="CLI utilities for the auth service.",
)


@app.callback()
def cli() -> None:
    """Auth service command-line interface."""


@app.command("create-superuser")
def create_superuser(
    login: Annotated[
        str,
        typer.Option(
            "--login",
            "-l",
            prompt=True,
            help="Superuser login.",
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
        async with async_session() as session:
            user_service = UserService(session)
            await user_service.create_user(
                login=login,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_superuser=True,
            )

    try:
        login = validate_login(login)
        password = validate_strong_password(password)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    try:
        asyncio.run(_run())
    except UserAlreadyExistsError:
        typer.secho(
            f"User with login '{login}' already exists.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1) from None

    typer.secho(
        f"Superuser '{login}' created successfully.",
        fg=typer.colors.GREEN,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
