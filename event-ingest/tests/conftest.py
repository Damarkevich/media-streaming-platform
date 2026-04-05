import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from flask_jwt_extended import create_access_token

SRC_DIR = Path(__file__).resolve().parents[1] / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

os.environ.setdefault("AUTHJWT_SECRET_KEY", "12345678901234567890123456789012")

from app import create_app


class FakeFuture:
    def __init__(self) -> None:
        self.errback = None

    def add_errback(self, callback):
        self.errback = callback
        return self


class FakeProducer:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, object]] = []
        self.flushed = False
        self.closed = False

    def send(
        self,
        topic: str,
        value: bytes | None = None,
        key: bytes | None = None,
        **_: object,
    ) -> FakeFuture:
        future = FakeFuture()
        self.sent_messages.append(
            {"topic": topic, "key": key, "value": value, "future": future}
        )
        return future

    def flush(self) -> None:
        self.flushed = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def producer() -> FakeProducer:
    return FakeProducer()


@pytest.fixture
def app(producer: FakeProducer):
    flask_app = create_app(producer_factory=lambda: producer)
    flask_app.testing = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app) -> dict[str, str]:
    with app.app_context():
        token = create_access_token(identity="user-123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_event():
    def _factory(**overrides: object) -> dict[str, object]:
        event = {
            "event_id": str(uuid4()),
            "event_type": "page_view",
            "event_timestamp": 1_744_000_000,
            "session_id": str(uuid4()),
            "context": {"device": "mobile"},
            "payload": {"page": "/movies"},
        }
        event.update(overrides)
        return event

    return _factory
