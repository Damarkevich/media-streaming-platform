def validate_strong_password(value: str) -> str:
    if not any("A" <= ch <= "Z" for ch in value):
        raise ValueError("password must contain at least one uppercase English letter")
    if not any("a" <= ch <= "z" for ch in value):
        raise ValueError("password must contain at least one lowercase English letter")
    if not any(ch.isdigit() for ch in value):
        raise ValueError("password must contain at least one digit")
    if not any(not ch.isalnum() for ch in value):
        raise ValueError("password must contain at least one special character")
    return value


def validate_login(value: str) -> str:
    if not value.isalnum():
        raise ValueError("login must be alphanumeric")
    return value
