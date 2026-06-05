from uuid import UUID

from fastapi import Header, HTTPException, status


def get_user_id_header(x_user_id: str = Header(alias="X-User-Id")) -> UUID:
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-User-Id must be a valid UUID.",
        ) from exc
