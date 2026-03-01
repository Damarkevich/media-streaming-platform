from sqlalchemy.exc import IntegrityError

POSTGRES_UNIQUE_VIOLATION_SQLSTATE = "23505"


def is_field_unique_violation(exc: IntegrityError, field_name: str) -> bool:
    """Check whether an IntegrityError is a unique violation for a specific field.

    This helper is intentionally conservative: it returns True only when the
    underlying database error looks like a Postgres unique-constraint violation
    and the constraint/message indicates it relates to the specified field.

    Args:
        exc: SQLAlchemy IntegrityError raised during commit.
        field_name: The name of the field to check for uniqueness violation.

    Returns:
        True if the error most likely represents a duplicate value for the specified field.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    if sqlstate != POSTGRES_UNIQUE_VIOLATION_SQLSTATE:
        return False

    constraint = getattr(orig, "constraint_name", None)
    if isinstance(constraint, str) and field_name in constraint.lower():
        return True

    return field_name in str(orig).lower()
