import pytest

from src.models.user import User


@pytest.mark.asyncio
async def test_user_set_password_hashes_password_and_keeps_check_working() -> None:
    """Ensure setting password stores hash and preserves password verification."""
    password_hash = await User.hash_password("InitialPass1!")
    user = User(
        login="hash_user",
        password_hash=password_hash,
        first_name="Ivan",
        last_name="Ivanov",
    )

    original_hash = user.password
    await user.set_password("NewStrongPass1!")

    assert user.password != "NewStrongPass1!"
    assert user.password != original_hash
    assert await user.check_password("NewStrongPass1!") is True


def test_user_constructor_rejects_raw_password_in_password_hash_field() -> None:
    """Ensure constructor enforces hashed password contract."""
    with pytest.raises(
        ValueError, match="password_hash must be a Werkzeug password hash"
    ):
        User(
            login="raw_user",
            password_hash="PlainTextPass1!",
            first_name="Ivan",
            last_name="Ivanov",
        )
