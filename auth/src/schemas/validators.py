def validate_strong_password(value: str) -> str:
    """Validate password complexity constraints.

    Args:
        value: Candidate password string.

    Returns:
        Original password when it satisfies all rules.

    Raises:
        ValueError: If at least one complexity rule is violated.
    """
    if not any("A" <= ch <= "Z" for ch in value):
        msg = "password must contain at least one uppercase English letter"
        raise ValueError(msg)
    if not any("a" <= ch <= "z" for ch in value):
        msg = "password must contain at least one lowercase English letter"
        raise ValueError(msg)
    if not any(ch.isdigit() for ch in value):
        msg = "password must contain at least one digit"
        raise ValueError(msg)
    if not any(not ch.isalnum() for ch in value):
        msg = "password must contain at least one special character"
        raise ValueError(msg)
    return value
