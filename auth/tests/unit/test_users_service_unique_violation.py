from sqlalchemy.exc import IntegrityError

from src.services.utils import is_field_unique_violation


class FakeOrigError:
    """Minimal DBAPI error stub for IntegrityError simulation."""

    def __init__(
        self,
        *,
        sqlstate: str | None = None,
        pgcode: str | None = None,
        constraint_name: str | None = None,
        message: str = "",
    ):
        self.sqlstate = sqlstate
        self.pgcode = pgcode
        self.constraint_name = constraint_name
        self._message = message

    def __str__(self) -> str:
        return self._message


def _make_integrity_error(orig: FakeOrigError) -> IntegrityError:
    """Wrap fake DBAPI error into SQLAlchemy IntegrityError."""
    return IntegrityError("statement", {}, orig)


def test_is_login_unique_violation_returns_true_for_login_constraint() -> None:
    """Ensure login constraint name is recognized as unique violation."""
    exc = _make_integrity_error(
        FakeOrigError(
            sqlstate="23505",
            constraint_name="users_login_key",
            message="duplicate key value violates unique constraint users_login_key",
        )
    )

    assert is_field_unique_violation(exc, "login") is True


def test_is_login_unique_violation_returns_true_when_login_in_message() -> None:
    """Ensure login mention in DB error message is recognized."""
    exc = _make_integrity_error(
        FakeOrigError(
            pgcode="23505",
            message="duplicate key value violates unique constraint login_unique",
        )
    )

    assert is_field_unique_violation(exc, "login") is True


def test_is_login_unique_violation_returns_false_for_other_sqlstate() -> None:
    """Ensure non-unique SQLSTATE is not treated as login uniqueness error."""
    exc = _make_integrity_error(
        FakeOrigError(
            sqlstate="23503",
            constraint_name="users_login_key",
            message="foreign key violation",
        )
    )

    assert is_field_unique_violation(exc, "login") is False
