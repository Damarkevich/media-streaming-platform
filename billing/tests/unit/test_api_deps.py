from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.api.deps import get_user_id_header


def test_get_user_id_header_returns_uuid() -> None:
    user_id = uuid4()

    result = get_user_id_header(str(user_id))

    assert result == user_id


def test_get_user_id_header_raises_for_invalid_value() -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_user_id_header("not-a-uuid")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "X-User-Id must be a valid UUID."
