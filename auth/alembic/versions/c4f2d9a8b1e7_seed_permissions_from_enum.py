"""seed permissions from enum

Revision ID: c4f2d9a8b1e7
Revises: b8d7f6c3a2e1
Create Date: 2026-03-01 19:05:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f2d9a8b1e7"
down_revision: Union[str, Sequence[str], None] = "b8d7f6c3a2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS_TO_ADD: tuple[str, ...] = (
    "permissions:read",
    "permissions:create",
    "permissions:update",
    "permissions:delete",
    "permissions:assign",
    "roles:read",
    "roles:create",
    "roles:update",
    "roles:delete",
    "roles:assign",
)


def upgrade() -> None:
    """Upgrade schema."""
    now_utc = datetime.now(timezone.utc)
    bind = op.get_bind()

    for permission_name in PERMISSIONS_TO_ADD:
        bind.execute(
            sa.text(
                """
                INSERT INTO auth.permissions (id, name, created_at)
                VALUES (:id, :name, :created_at)
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "name": permission_name,
                "created_at": now_utc,
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM auth.permissions
            WHERE name = ANY(:permission_names)
            """
        ),
        {"permission_names": list(PERMISSIONS_TO_ADD)},
    )
