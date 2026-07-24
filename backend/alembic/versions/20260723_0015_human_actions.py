"""Add human_actions table for persistent human action tracking.

Revision ID: 20260723_0015
Revises: 20260722_0014
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0015"
down_revision: str | Sequence[str] | None = "20260722_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "human_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "resolved",
                "cancelled",
                name="human_action_status",
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "assigned_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("assigned_role", sa.String(50), nullable=True),
        sa.Column(
            "decision_package",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "response",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["business_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index(
            "ix_human_actions_company_status",
            "company_id",
            "status",
        ),
        sa.Index(
            "ix_human_actions_company_due",
            "company_id",
            "due_date",
        ),
        sa.Index(
            "ix_human_actions_request",
            "request_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("human_actions")
