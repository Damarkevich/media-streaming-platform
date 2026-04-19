from async_fastapi_jwt_auth import AuthJWT  # type: ignore[import-untyped]
from async_fastapi_jwt_auth.auth_jwt import (
    AuthJWTBearer,  # type: ignore[import-untyped]
)

from src.core.config import Settings, settings
from src.services.redis import create_redis_client

auth_dep = AuthJWTBearer()


@AuthJWT.load_config  # type: ignore[arg-type]
def get_config() -> Settings:
    """Provide JWT library configuration from application settings."""
    return settings


@AuthJWT.token_in_denylist_loader  # type: ignore[arg-type]
async def check_if_token_in_blacklist(
    decrypted_token: dict[str, str | int | bool],
) -> bool:
    """Check whether a JWT is revoked.

    Token blacklist is stored in Redis.
    If jwt is missing JTI or type claim, it is treated as revoked.
    If underlying storage is unavailable, this check
    fails closed and treats token as revoked.
    """
    jti = str(decrypted_token.get("jti", ""))
    if not jti:
        return True

    token_type = str(decrypted_token.get("type", "")).strip().lower()
    redis_service = await create_redis_client()
    return await redis_service.is_token_blacklisted(jti=jti, token_type=token_type)
