import pytest
from pydantic import ValidationError

from src.core.config import Settings

TEST_POSTGRES_PASSWORD = "db-password"
VALID_AUTHJWT_SECRET_KEY = "super-secret-key-that-is-at-least-32-chars"
VALID_SESSION_SECRET_KEY = "super-session-key-that-is-at-least-32-chars"
VALID_GOOGLE_CLIENT_ID = "google-client-id"
VALID_GOOGLE_CLIENT_SECRET = "google-client-secret"


REQUIRED_ENV_VARS = [
    ("postgres_password", TEST_POSTGRES_PASSWORD),
    ("authjwt_secret_key", VALID_AUTHJWT_SECRET_KEY),
    ("session_secret_key", VALID_SESSION_SECRET_KEY),
    ("google_client_id", VALID_GOOGLE_CLIENT_ID),
    ("google_client_secret", VALID_GOOGLE_CLIENT_SECRET),
]


@pytest.mark.parametrize("missing_var,valid_value", REQUIRED_ENV_VARS)
def test_settings_requires_required_vars(
    monkeypatch: pytest.MonkeyPatch, missing_var, valid_value
) -> None:
    """Ensure settings validation fails when any required variable is missing."""
    # Prepare kwargs with all valid values
    kwargs = {
        "authjwt_secret_key": VALID_AUTHJWT_SECRET_KEY,
        "session_secret_key": VALID_SESSION_SECRET_KEY,
        "google_client_id": VALID_GOOGLE_CLIENT_ID,
        "google_client_secret": VALID_GOOGLE_CLIENT_SECRET,
        "postgres_password": TEST_POSTGRES_PASSWORD,
    }
    # Remove the required variable under test
    kwargs.pop(missing_var)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize(
    "field,blank_value",
    [
        ("authjwt_secret_key", "   "),
        ("session_secret_key", "   "),
    ],
)
def test_settings_rejects_blank_required_vars(field, blank_value):
    """Ensure settings validation fails for blank required secrets/keys."""
    kwargs = {
        "authjwt_secret_key": VALID_AUTHJWT_SECRET_KEY,
        "session_secret_key": VALID_SESSION_SECRET_KEY,
        "google_client_id": VALID_GOOGLE_CLIENT_ID,
        "google_client_secret": VALID_GOOGLE_CLIENT_SECRET,
        "postgres_password": TEST_POSTGRES_PASSWORD,
    }
    kwargs[field] = blank_value
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, **kwargs)
    assert "should be at least 32 characters" in str(exc_info.value)


def test_settings_accepts_all_valid_required_vars() -> None:
    """Ensure settings accept all valid required variables."""
    settings = Settings(
        _env_file=None,
        authjwt_secret_key=VALID_AUTHJWT_SECRET_KEY,
        session_secret_key=VALID_SESSION_SECRET_KEY,
        google_client_id=VALID_GOOGLE_CLIENT_ID,
        google_client_secret=VALID_GOOGLE_CLIENT_SECRET,
        postgres_password=TEST_POSTGRES_PASSWORD,
    )
    assert settings.authjwt_secret_key == VALID_AUTHJWT_SECRET_KEY
    assert settings.session_secret_key == VALID_SESSION_SECRET_KEY
    assert settings.google_client_id == VALID_GOOGLE_CLIENT_ID
    assert settings.google_client_secret == VALID_GOOGLE_CLIENT_SECRET
    assert settings.postgres_password == TEST_POSTGRES_PASSWORD
