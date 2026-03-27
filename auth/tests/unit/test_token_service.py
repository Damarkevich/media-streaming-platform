from datetime import timedelta
from unittest.mock import AsyncMock, call
from uuid import uuid4

import pytest

from src.services.tokens import TokenService


@pytest.mark.asyncio
async def test_issue_tokens_uses_configured_ttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure token service uses configured TTL values for token creation."""
    monkeypatch.setattr("src.services.tokens.settings.access_token_expires", 101)
    monkeypatch.setattr("src.services.tokens.settings.refresh_token_expires", 202)

    auth = AsyncMock()
    redis_client = AsyncMock()
    auth.create_access_token.return_value = "access-token"
    auth.create_refresh_token.return_value = "refresh-token"

    service = TokenService(auth=auth, redis_client=redis_client)
    user_id = uuid4()
    roles_names = ["subscriber"]
    access_token, refresh_token = await service.issue_tokens(user_id, roles_names)

    assert access_token == "access-token"
    assert refresh_token == "refresh-token"
    auth.create_access_token.assert_awaited_once_with(
        subject=str(user_id),
        expires_time=timedelta(seconds=101),
        fresh=False,
        user_claims={"roles": roles_names},
    )
    auth.create_refresh_token.assert_awaited_once_with(
        subject=str(user_id), expires_time=timedelta(seconds=202)
    )


@pytest.mark.asyncio
async def test_add_refresh_to_blacklist_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure adding same refresh JTI twice remains safe and idempotent (Redis)."""
    monkeypatch.setattr("src.services.tokens.settings.refresh_token_expires", 10000)
    auth = AsyncMock()
    redis_client = AsyncMock()
    service = TokenService(auth=auth, redis_client=redis_client)

    await service.add_token_to_blacklist("same-jti", token_type="refresh")
    await service.add_token_to_blacklist("same-jti", token_type="refresh")

    assert redis_client.add_token_to_blacklist.await_count == 2
    redis_client.add_token_to_blacklist.assert_has_calls(
        [
            call(
                jti="same-jti",
                ttl_seconds=10000,
                token_type="refresh",
            ),
            call(
                jti="same-jti",
                ttl_seconds=10000,
                token_type="refresh",
            ),
        ]
    )
