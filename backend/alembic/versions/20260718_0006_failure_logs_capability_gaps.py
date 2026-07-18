"""Create failure logs and capability gaps.

Revision ID: 20260718_0006
Revises: 20260718_0005
Create Date: 2026-07-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260718_0006"
down_revision: str | Sequence[str] | None = "20260718_0005"
branch_labels = None
depends_on = None

failure_type = postgresql.ENUM(
    "tool_failure",
    "database_failure",
    "retrieval_failure",
    "external_service_failure",
    "validation_failure",
    "authorization_failure",
    "workflow_failure",
    "configuration_failure",
    "unexpected_failure",
    name="failure_type",
    create_type=False,
)
failure_source = postgresql.ENUM(
    "api",
    "service",
    "repository",
    "tool",
    "workflow",
    "rag",
    "llm",
    "external_service",
    "system",
    name="failure_source",
    create_type=False,
)
gap_status = postgresql.ENUM(
    "open",
    "acknowledged",
    "planned",
    "resolved",
    "rejected",
    name="capability_gap_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    failure_type.create(bind, checkfirst=True)
    failure_source.create(bind, checkfirst=True)
    gap_status.create(bind, checkfirst=True)
    op.execute(
        "ALTER TYPE workflow_event_type ADD VALUE IF NOT EXISTS 'failure_recorded'"
    )
    op.execute(
        "ALTER TYPE workflow_event_type ADD VALUE IF NOT EXISTS 'capability_gap_detected'"
    )
    op.drop_constraint(
        "ck_business_requests_owner_for_owned_status",
        "business_requests",
        type_="check",
    )
    op.create_check_constraint(
        "ck_business_requests_owner_for_owned_status",
        "business_requests",
        "status IN ('created', 'routing', 'cancelled', 'failed') "
        "OR owner_department_id IS NOT NULL",
    )
    op.add_column(
        "business_requests",
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_business_requests_failed_timestamp",
        "business_requests",
        "status != 'failed' OR failed_at IS NOT NULL",
    )

    op.create_table(
        "failure_logs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_type", failure_type, nullable=False),
        sa.Column("failure_source", failure_source, nullable=False),
        sa.Column("failed_operation", sa.String(255), nullable=False),
        sa.Column("internal_message", sa.Text(), nullable=False),
        sa.Column("safe_message", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column(
            "technical_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "alternative_attempted",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("alternative_description", sa.Text(), nullable=True),
        sa.Column(
            "is_terminal", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "resolved OR (resolved_at IS NULL AND resolved_by_user_id IS NULL)",
            name="ck_failure_logs_unresolved_fields",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["request_id"], ["business_requests.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (
        ("ix_failure_logs_company_request", ["company_id", "request_id"]),
        ("ix_failure_logs_company_department", ["company_id", "department_id"]),
        ("ix_failure_logs_company_type", ["company_id", "failure_type"]),
        ("ix_failure_logs_company_created", ["company_id", "created_at"]),
        ("ix_failure_logs_company_resolved", ["company_id", "resolved"]),
    ):
        op.create_index(name, "failure_logs", columns)

    op.create_table(
        "capability_gaps",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_operation", sa.String(255), nullable=False),
        sa.Column("normalized_operation", sa.String(255), nullable=False),
        sa.Column("deduplication_key", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("safe_user_message", sa.Text(), nullable=False),
        sa.Column(
            "status", gap_status, server_default=sa.text("'open'"), nullable=False
        ),
        sa.Column(
            "occurrence_count",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint(
            "occurrence_count > 0", name="ck_capability_gaps_positive_occurrences"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["request_id"], ["business_requests.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_capability_gaps_company_status", "capability_gaps", ["company_id", "status"]
    )
    op.create_index(
        "ix_capability_gaps_company_department",
        "capability_gaps",
        ["company_id", "department_id"],
    )
    op.create_index(
        "ix_capability_gaps_company_last_seen",
        "capability_gaps",
        ["company_id", "last_seen_at"],
    )
    op.create_index(
        "uq_capability_gaps_unresolved_dedup",
        "capability_gaps",
        ["company_id", "deduplication_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('open', 'acknowledged', 'planned')"),
    )


def downgrade() -> None:
    for name in (
        "uq_capability_gaps_unresolved_dedup",
        "ix_capability_gaps_company_last_seen",
        "ix_capability_gaps_company_department",
        "ix_capability_gaps_company_status",
    ):
        op.drop_index(name, table_name="capability_gaps")
    op.drop_table("capability_gaps")
    for name in (
        "ix_failure_logs_company_resolved",
        "ix_failure_logs_company_created",
        "ix_failure_logs_company_type",
        "ix_failure_logs_company_department",
        "ix_failure_logs_company_request",
    ):
        op.drop_index(name, table_name="failure_logs")
    op.drop_table("failure_logs")
    op.drop_constraint(
        "ck_business_requests_failed_timestamp", "business_requests", type_="check"
    )
    op.drop_column("business_requests", "failed_at")
    op.drop_constraint(
        "ck_business_requests_owner_for_owned_status",
        "business_requests",
        type_="check",
    )
    op.create_check_constraint(
        "ck_business_requests_owner_for_owned_status",
        "business_requests",
        "status IN ('created', 'routing', 'cancelled') "
        "OR owner_department_id IS NOT NULL",
    )
    op.execute(
        "DELETE FROM workflow_events WHERE event_type::text IN ('failure_recorded', 'capability_gap_detected')"
    )
    op.execute(
        "ALTER TABLE workflow_events ALTER COLUMN event_type TYPE text USING event_type::text"
    )
    op.execute("DROP TYPE workflow_event_type")
    op.execute(
        "CREATE TYPE workflow_event_type AS ENUM ('request_created','routing_started','request_routed','stage_started','stage_completed','department_collaboration_started','department_collaboration_completed','waiting_for_human_approval','waiting_for_human_action','review_started','review_completed','request_resumed','request_completed','request_rejected','request_cancelled','request_failed')"
    )
    op.execute(
        "ALTER TABLE workflow_events ALTER COLUMN event_type TYPE workflow_event_type USING event_type::workflow_event_type"
    )
    gap_status.drop(op.get_bind(), checkfirst=True)
    failure_source.drop(op.get_bind(), checkfirst=True)
    failure_type.drop(op.get_bind(), checkfirst=True)
