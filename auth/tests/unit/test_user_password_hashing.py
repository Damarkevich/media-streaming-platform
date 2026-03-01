from src.models.user import User


def test_user_set_password_hashes_password_and_keeps_check_working() -> None:
    user = User(
        login="hash_user",
        password="InitialPass1!",
        first_name="Ivan",
        last_name="Ivanov",
    )

    original_hash = user.password
    user.set_password("NewStrongPass1!")

    assert user.password != "NewStrongPass1!"
    assert user.password != original_hash
    assert user.check_password("NewStrongPass1!") is True
