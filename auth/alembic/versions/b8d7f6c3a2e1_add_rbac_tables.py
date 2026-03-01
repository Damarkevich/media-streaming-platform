"""add rbac tables

Revision ID: b8d7f6c3a2e1
Revises: 344ef5ae1f5a
Create Date: 2026-03-01 18:25:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8d7f6c3a2e1"
down_revision: Union[str, Sequence[str], None] = "344ef5ae1f5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_SUPERUSER_ID = uuid.UUID("6fcb7f9b-a070-4ee6-850e-4e6c63c357aa")
ROLE_ADMIN_ID = uuid.UUID("f1569378-f1f0-4d75-8bf6-f636de3cc74a")
ROLE_SUBSCRIBER_ID = uuid.UUID("a15f7c6a-8c2e-40d8-bf34-f1efb7f22fb3")
ROLE_NONSUBSCRIBER_ID = uuid.UUID("e0f17e8d-8a53-4fc3-bf7d-2f6ecab95d5d")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="auth",
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema="auth",
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth.roles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
        schema="auth",
    )
    op.create_index(
        "ix_user_roles_user_id", "user_roles", ["user_id"], unique=False, schema="auth"
    )
    op.create_index(
        "ix_user_roles_role_id", "user_roles", ["role_id"], unique=False, schema="auth"
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["auth.permissions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["auth.roles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        schema="auth",
    )
    op.create_index(
        "ix_role_permissions_role_id",
        "role_permissions",
        ["role_id"],
        unique=False,
        schema="auth",
    )
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
        unique=False,
        schema="auth",
    )

    roles = sa.table(
        "roles",
        sa.column("id", sa.UUID()),
        sa.column("name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        schema="auth",
    )
    now_utc = datetime.now(timezone.utc)
    op.bulk_insert(
        roles,
        [
            {"id": ROLE_SUPERUSER_ID, "name": "superuser", "created_at": now_utc},
            {"id": ROLE_ADMIN_ID, "name": "admin", "created_at": now_utc},
            {"id": ROLE_SUBSCRIBER_ID, "name": "subscriber", "created_at": now_utc},
            {
                "id": ROLE_NONSUBSCRIBER_ID,
                "name": "nonsubscriber",
                "created_at": now_utc,
            },
        ],
        multiinsert=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_role_permissions_permission_id",
        table_name="role_permissions",
        schema="auth",
    )
    op.drop_index(
        "ix_role_permissions_role_id", table_name="role_permissions", schema="auth"
    )
    op.drop_table("role_permissions", schema="auth")

    op.drop_index("ix_user_roles_role_id", table_name="user_roles", schema="auth")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles", schema="auth")
    op.drop_table("user_roles", schema="auth")

    op.drop_table("permissions", schema="auth")
    op.drop_table("roles", schema="auth")
