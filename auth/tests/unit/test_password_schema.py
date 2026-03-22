import pytest
from pydantic import ValidationError

from src.schemas.users import UserCreate


def _valid_payload(password: str) -> dict[str, str]:
    """Build a valid base payload with customizable password value."""
    return {
        "email": "user01@example.com",
        "password": password,
        "first_name": "Ivan",
        "last_name": "Ivanov",
    }


def test_user_create_accepts_strong_password() -> None:
    """Ensure schema accepts passwords that satisfy all complexity rules."""
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
    """Ensure schema rejects weak passwords with informative errors."""
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(**_valid_payload(password))

    assert expected_message in str(exc_info.value)
