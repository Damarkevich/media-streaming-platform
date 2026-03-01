"""remove unused permissions

Revision ID: e9b4c7a1d2f3
Revises: c4f2d9a8b1e7
Create Date: 2026-03-01 20:30:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9b4c7a1d2f3"
down_revision: Union[str, Sequence[str], None] = "c4f2d9a8b1e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REMOVED_PERMISSIONS: tuple[str, ...] = (
    "permissions:create",
    "permissions:update",
    "permissions:delete",
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM auth.permissions
            WHERE name = ANY(:permission_names)
            """
        ),
        {"permission_names": list(REMOVED_PERMISSIONS)},
    )


def downgrade() -> None:
    """Downgrade schema."""
    now_utc = datetime.now(timezone.utc)
    bind = op.get_bind()

    for permission_name in REMOVED_PERMISSIONS:
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
