import pytest
from pydantic import ValidationError

from src.schemas.entity import UserCreate


def _valid_payload(password: str) -> dict[str, str]:
    return {
        "login": "user_01",
        "password": password,
        "first_name": "Ivan",
        "last_name": "Ivanov",
    }


def test_user_create_accepts_strong_password() -> None:
    user = UserCreate(**_valid_payload("StrongPass1!"))
    assert user.password == "StrongPass1!"


@pytest.mark.parametrize(
    "password,expected_message",
    [
        ("lowercase1!", "uppercase English letter"),
        ("UPPERCASE1!", "lowercase English letter"),
        ("NoDigits!!", "at least one digit"),
        ("NoSpecial1", "at least one special character"),
    ],
)
def test_user_create_rejects_weak_password(
    password: str, expected_message: str
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**_valid_payload(password))

    assert expected_message in str(exc_info.value)
