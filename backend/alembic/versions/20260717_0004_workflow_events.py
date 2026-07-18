"""Create the persistent tenant-scoped workflow event timeline.

Revision ID: 20260717_0004
Revises: 20260717_0003
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260717_0004"
down_revision: str | Sequence[str] | None = "20260717_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


workflow_event_type_enum = postgresql.ENUM(
    "request_created",
    "routing_started",
    "request_routed",
    "stage_started",
    "stage_completed",
    "department_collaboration_started",
    "department_collaboration_completed",
    "waiting_for_human_approval",
    "waiting_for_human_action",
    "review_started",
    "review_completed",
    "request_resumed",
    "request_completed",
    "request_rejected",
    "request_cancelled",
    "request_failed",
    name="workflow_event_type",
    create_type=False,
)
workflow_event_actor_type_enum = postgresql.ENUM(
    "system",
    "router",
    "department_agent",
    "reviewer",
    "user",
    "manager",
    "company_account",
    "tool",
    name="workflow_event_actor_type",
    create_type=False,
)
workflow_event_visibility_enum = postgresql.ENUM(
    "requester",
    "manager",
    "company",
    "internal",
    name="workflow_event_visibility",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    workflow_event_type_enum.create(bind, checkfirst=True)
    workflow_event_actor_type_enum.create(bind, checkfirst=True)
    workflow_event_visibility_enum.create(bind, checkfirst=True)

    op.create_table(
        "workflow_events",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", workflow_event_type_enum, nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("actor_type", workflow_event_actor_type_enum, nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("visibility", workflow_event_visibility_enum, nullable=False),
        sa.Column(
            "event_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_workflow_events_positive_sequence",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_workflow_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_workflow_events_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_workflow_events_department_id_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["business_requests.id"],
            name="fk_workflow_events_request_id_business_requests",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflow_events"),
        sa.UniqueConstraint(
            "request_id",
            "sequence_number",
            name="uq_workflow_events_request_sequence",
        ),
    )
    op.create_index(
        "ix_workflow_events_company_request_sequence",
        "workflow_events",
        ["company_id", "request_id", "sequence_number"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workflow_events_company_request_sequence",
        table_name="workflow_events",
    )
    op.drop_table("workflow_events")
    workflow_event_visibility_enum.drop(op.get_bind(), checkfirst=True)
    workflow_event_actor_type_enum.drop(op.get_bind(), checkfirst=True)
    workflow_event_type_enum.drop(op.get_bind(), checkfirst=True)
