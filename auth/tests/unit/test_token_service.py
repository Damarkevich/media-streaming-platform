from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.services.tokens import TokenService


@pytest.mark.asyncio
async def test_issue_tokens_uses_configured_ttls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.services.tokens.settings.access_token_expires", 101)
    monkeypatch.setattr("src.services.tokens.settings.refresh_token_expires", 202)

    db = AsyncMock()
    auth = AsyncMock()
    redis_client = AsyncMock()
    auth.create_access_token.return_value = "access-token"
    auth.create_refresh_token.return_value = "refresh-token"

    service = TokenService(db=db, auth=auth, redis_client=redis_client)
    user_id = uuid4()
    access_token, refresh_token = await service.issue_tokens(user_id)

    assert access_token == "access-token"
    assert refresh_token == "refresh-token"
    auth.create_access_token.assert_awaited_once_with(
        subject=str(user_id), expires_time=timedelta(seconds=101), fresh=False
    )
    auth.create_refresh_token.assert_awaited_once_with(
        subject=str(user_id), expires_time=timedelta(seconds=202)
    )


@pytest.mark.asyncio
async def test_add_refresh_to_blacklist_is_idempotent() -> None:
    db = AsyncMock()
    auth = AsyncMock()
    redis_client = AsyncMock()

    service = TokenService(db=db, auth=auth, redis_client=redis_client)

    await service.add_refresh_to_blacklist("same-jti")
    await service.add_refresh_to_blacklist("same-jti")

    assert db.execute.await_count == 2
    assert db.commit.await_count == 2
