import os
import sys
from pathlib import Path


def pytest_sessionstart(session) -> None:  # type: ignore[no-untyped-def]
    # Ensure settings can be imported in tests without relying on external env.
    os.environ.setdefault("CLICKHOUSE_DEFAULT_PASSWORD", "test-password")

    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
