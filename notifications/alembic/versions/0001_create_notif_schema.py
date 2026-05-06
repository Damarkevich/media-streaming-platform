"""create notif schema with templates, campaigns, jobs, deliveries tables

Revision ID: 0001
Revises:
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "notif"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    op.create_table(
        "templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("subject_template", sa.Text, nullable=False),
        sa.Column("body_template", sa.Text, nullable=False),
        sa.Column("required_variables", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_templates_notification_type", "templates", ["notification_type"], schema=SCHEMA)

    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("campaign_type", sa.String(50), nullable=False),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("template_variables", JSONB, nullable=False, server_default="{}"),
        sa.Column("audience", sa.String(50), nullable=False, server_default="ALL_USERS"),
        sa.Column("status", sa.String(50), nullable=False, server_default="DRAFT"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_campaigns_status", "campaigns", ["status"], schema=SCHEMA)
    op.create_index("ix_campaigns_campaign_type", "campaigns", ["campaign_type"], schema=SCHEMA)

    op.create_table(
        "jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("campaign_type", sa.String(50), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_jobs_status_next_run_at", "jobs", ["status", "next_run_at"], schema=SCHEMA)

    op.create_table(
        "deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="EMAIL"),
        sa.Column("idempotency_key", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_deliveries_user_id", "deliveries", ["user_id"], schema=SCHEMA)
    op.create_index("ix_deliveries_status", "deliveries", ["status"], schema=SCHEMA)
    op.create_index("ix_deliveries_campaign_id", "deliveries", ["campaign_id"], schema=SCHEMA)
    op.create_index(
        "ix_deliveries_idempotency_key",
        "deliveries",
        ["idempotency_key"],
        unique=True,
        schema=SCHEMA,
    )

    # Seed initial templates
    op.execute(f"""
        INSERT INTO "{SCHEMA}".templates
            (id, name, notification_type, subject_template, body_template, required_variables)
        VALUES
        (
            gen_random_uuid(),
            'manual_campaign',
            'MANUAL_CAMPAIGN',
            'Important update for you',
            '<p>Hello, {{{{ first_name }}}}!</p><p>{{{{ custom_message }}}}</p>',
            '["first_name", "custom_message"]'
        ),
        (
            gen_random_uuid(),
            'weekly_digest',
            'WEEKLY_DIGEST',
            'Your weekend watchlist 🎬',
            '<p>Hello, {{{{ first_name }}}}!</p><p>Top 10 films this week:</p>{{{{ films_list }}}}',
            '["first_name", "films_list"]'
        ),
        (
            gen_random_uuid(),
            'review_liked',
            'REVIEW_LIKED',
            'Someone liked your review!',
            '<p>Hello, {{{{ first_name }}}}!</p><p>Your review &ldquo;{{{{ review_text_preview }}}}&rdquo; has {{{{ likes_count }}}} like(s).</p>',
            '["first_name", "review_text_preview", "likes_count"]'
        )
    """)

    # Seed weekly digest job
    op.execute(f"""
        INSERT INTO "{SCHEMA}".jobs
            (id, name, campaign_type, cron_expression, status, template_id)
        SELECT
            gen_random_uuid(),
            'weekly_digest',
            'WEEKLY_DIGEST',
            '0 9 * * 5',
            'ACTIVE',
            id
        FROM "{SCHEMA}".templates
        WHERE name = 'weekly_digest'
        LIMIT 1
    """)


def downgrade() -> None:
    op.drop_table("deliveries", schema=SCHEMA)
    op.drop_table("jobs", schema=SCHEMA)
    op.drop_table("campaigns", schema=SCHEMA)
    op.drop_table("templates", schema=SCHEMA)
    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}"')
