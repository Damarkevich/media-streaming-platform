"""seed permissions

Revision ID: 69cc3d7b038c
Revises: c41fd2888559
Create Date: 2026-03-02 19:49:43.448513

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "69cc3d7b038c"
down_revision: str | Sequence[str] | None = "c41fd2888559"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS_TO_ADD: tuple[str, ...] = (
    "permissions:read",
    "permissions:assign",
    "roles:read",
    "roles:create",
    "roles:update",
    "roles:delete",
    "roles:assign",
    "content:read",
    "content:create",
    "content:update",
    "content:delete",
)


def upgrade() -> None:
    """Upgrade schema."""
    for permission_name in PERMISSIONS_TO_ADD:
        op.execute(
            sa.text(
                """
                INSERT INTO auth.permissions (id, name, created_at)
                VALUES (CAST(:id AS uuid), :name, NOW())
                ON CONFLICT (name) DO NOTHING
                """
            ).bindparams(id=str(uuid4()), name=permission_name)
        )


def downgrade() -> None:
    """Downgrade schema."""
    for permission_name in PERMISSIONS_TO_ADD:
        op.execute(
            sa.text("DELETE FROM auth.permissions WHERE name = :name").bindparams(
                name=permission_name
            )
        )
