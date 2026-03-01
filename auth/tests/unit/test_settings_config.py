import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_settings_requires_authjwt_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure settings validation fails when JWT secret is missing."""
    monkeypatch.delenv("AUTHJWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_empty_authjwt_secret_key() -> None:
    """Ensure settings validation fails for blank JWT secret."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, authjwt_secret_key="   ")

    assert "AUTHJWT_SECRET_KEY must not be empty" in str(exc_info.value)


def test_settings_accepts_non_empty_authjwt_secret_key() -> None:
    """Ensure settings accept a non-empty JWT secret value."""
    settings = Settings(_env_file=None, authjwt_secret_key="super-secret-key")

    assert settings.authjwt_secret_key == "super-secret-key"
