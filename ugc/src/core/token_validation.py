import logging
from typing import Any

from jose import jwt
from jose.exceptions import JWTError

from src.core.config import settings
from src.core.token_models import TokenPayload
from src.db.redis import get_redis

ACCESS_BLACKLIST_KEY_PREFIX = "blacklist:access:"

logger = logging.getLogger(__name__)


def decode_token(token: str) -> TokenPayload | None:
    """Decode JWT and return claims payload when valid."""
    try:
        decoded_token: dict[str, Any] = jwt.decode(
            token,
            settings.authjwt_secret_key,
            algorithms=[settings.authjwt_algorithm],
        )
        return TokenPayload(**decoded_token)
    except JWTError:
        return None


async def is_access_token_revoked(token_payload: TokenPayload) -> bool:
    """Check whether an access token is revoked using shared Redis denylist."""
    jti = str(token_payload.jti).strip()
    if not jti:
        return False

    try:
        redis = await get_redis()
        key = f"{ACCESS_BLACKLIST_KEY_PREFIX}{jti}"
        value = await redis.get(key)
    except Exception:
        logger.exception("Failed to validate access-token denylist status")
        return True
    else:
        return value is not None


async def is_token_type_not_access(token_payload: TokenPayload) -> bool:
    """Check whether token type is not access."""
    return str(token_payload.type).strip().lower() != "access"
