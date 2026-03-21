"""seed default roles

Revision ID: a1b2c3d4e5f6
Revises: 69cc3d7b038c
Create Date: 2026-03-21 13:18:30.775029

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "69cc3d7b038c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# role name -> list of permission names to assign
DEFAULT_ROLES_PERMISSIONS_MAP: dict[str, list[str]] = {
    "admin": [
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
    ],
    "subscriber": [
        "content:read",
    ],
}


def upgrade() -> None:
    """Upgrade schema."""
    for role_name, permission_names in DEFAULT_ROLES_PERMISSIONS_MAP.items():
        op.execute(
            sa.text(
                """
                WITH upserted_role AS (
                    INSERT INTO auth.roles (id, name, created_at)
                    VALUES (gen_random_uuid(), :role_name, NOW())
                    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                )
                INSERT INTO auth.role_permissions (role_id, permission_id)
                SELECT upserted_role.id, p.id
                FROM upserted_role
                JOIN auth.permissions p ON p.name = ANY(:permission_names)
                ON CONFLICT DO NOTHING
                """
            ).bindparams(
                role_name=role_name,
                permission_names=permission_names,
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    for role_name in DEFAULT_ROLES_PERMISSIONS_MAP:
        op.execute(
            sa.text(
                """
                DELETE FROM auth.role_permissions
                WHERE role_id = (SELECT id FROM auth.roles WHERE name = :name)
                """
            ).bindparams(name=role_name)
        )
        op.execute(
            sa.text("DELETE FROM auth.roles WHERE name = :name").bindparams(
                name=role_name
            )
        )
