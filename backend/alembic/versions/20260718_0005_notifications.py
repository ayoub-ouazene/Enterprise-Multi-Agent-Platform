"""Create persistent tenant-scoped user notifications.

Revision ID: 20260718_0005
Revises: 20260717_0004
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260718_0005"
down_revision: str | Sequence[str] | None = "20260717_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


notification_type_enum = postgresql.ENUM(
    "request_created",
    "request_status_changed",
    "request_completed",
    "request_rejected",
    "request_cancelled",
    "request_failed",
    "approval_required",
    "human_action_required",
    "information_required",
    "review_completed",
    "capability_gap",
    "system_notice",
    name="notification_type",
    create_type=False,
)
notification_severity_enum = postgresql.ENUM(
    "info",
    "success",
    "warning",
    "error",
    name="notification_severity",
    create_type=False,
)
notification_action_type_enum = postgresql.ENUM(
    "approve",
    "reject",
    "provide_information",
    "confirm_action",
    "view_request",
    "open_onboarding",
    "review_failure",
    name="notification_action_type",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    notification_type_enum.create(bind, checkfirst=True)
    notification_severity_enum.create(bind, checkfirst=True)
    notification_action_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notification_type", notification_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            notification_severity_enum,
            server_default=sa.text("'info'"),
            nullable=False,
        ),
        sa.Column(
            "action_required",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("action_type", notification_action_type_enum, nullable=True),
        sa.Column("action_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "NOT action_required OR action_type IS NOT NULL",
            name="ck_notifications_required_action_type",
        ),
        sa.CheckConstraint(
            "(is_read AND read_at IS NOT NULL) OR (NOT is_read AND read_at IS NULL)",
            name="ck_notifications_read_timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_notifications_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            name="fk_notifications_recipient_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["business_requests.id"],
            name="fk_notifications_request_id_business_requests",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "ix_notifications_company_recipient_created",
        "notifications",
        ["company_id", "recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_company_recipient_read",
        "notifications",
        ["company_id", "recipient_user_id", "is_read"],
    )
    op.create_index(
        "ix_notifications_company_request",
        "notifications",
        ["company_id", "request_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_company_request",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_company_recipient_read",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_company_recipient_created",
        table_name="notifications",
    )
    op.drop_table("notifications")
    notification_action_type_enum.drop(op.get_bind(), checkfirst=True)
    notification_severity_enum.drop(op.get_bind(), checkfirst=True)
    notification_type_enum.drop(op.get_bind(), checkfirst=True)
