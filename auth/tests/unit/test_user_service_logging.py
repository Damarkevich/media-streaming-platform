from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from src.models.log import LogType
from src.services.users import UserService


class FakeSession:
    """Session stub recording add/commit/rollback calls."""

    def __init__(self, *, fail_commit: bool = False) -> None:
        self.fail_commit = fail_commit
        self.add_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0

    def add(self, item) -> None:
        self.add_calls += 1

    async def commit(self) -> None:
        self.commit_calls += 1
        if self.fail_commit:
            raise SQLAlchemyError("commit failed")

    async def rollback(self) -> None:
        self.rollback_calls += 1


@pytest.mark.asyncio
async def test_log_user_action_commits_log_record() -> None:
    """Ensure successful log write commits without rollback."""
    session = FakeSession(fail_commit=False)
    service = UserService(session)  # type: ignore[arg-type]
    user = SimpleNamespace(id=uuid4())

    await service.log_user_action(user, LogType.LOGIN)

    assert session.add_calls == 1
    assert session.commit_calls == 1
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_log_user_action_swallows_db_error_and_rolls_back() -> None:
    """Ensure logging DB errors are swallowed with rollback."""
    session = FakeSession(fail_commit=True)
    service = UserService(session)  # type: ignore[arg-type]
    user = SimpleNamespace(id=uuid4())

    await service.log_user_action(user, LogType.LOGIN)

    assert session.add_calls == 1
    assert session.commit_calls == 1
    assert session.rollback_calls == 1
