from async_fastapi_jwt_auth import AuthJWT
from async_fastapi_jwt_auth.auth_jwt import AuthJWTBearer

from src.core.config import settings
from src.services.blacklist import check_token_revoked_runtime

auth_dep = AuthJWTBearer()


@AuthJWT.load_config
def get_config():
    return settings


@AuthJWT.token_in_denylist_loader
async def check_if_token_in_blacklist(
    decrypted_token: dict[str, str | int | bool],
) -> bool:
    """Check whether a JWT is revoked.

    Access-token blacklist is stored in Redis, refresh-token blacklist is
    persisted in PostgreSQL. If underlying storage is unavailable, this check
    fails closed and treats token as revoked.
    """
    jti = str(decrypted_token.get("jti", ""))
    if not jti:
        return False

    token_type = str(decrypted_token.get("type", "")).strip().lower()
    return await check_token_revoked_runtime(token_type=token_type, jti=jti)
