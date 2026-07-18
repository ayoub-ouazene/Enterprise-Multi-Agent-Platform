"""Create the tenant-owned business request core.

Revision ID: 20260717_0003
Revises: 20260716_0002
Create Date: 2026-07-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260717_0003"
down_revision: str | Sequence[str] | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


request_status_enum = postgresql.ENUM(
    "created",
    "routing",
    "processing",
    "waiting_for_department",
    "waiting_for_human_approval",
    "waiting_for_human_action",
    "under_review",
    "completed",
    "rejected",
    "cancelled",
    "failed",
    name="request_status",
    create_type=False,
)
request_priority_enum = postgresql.ENUM(
    "low",
    "normal",
    "high",
    "urgent",
    name="request_priority",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    request_status_enum.create(bind, checkfirst=True)
    request_priority_enum.create(bind, checkfirst=True)

    op.create_table(
        "business_requests",
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "requester_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "requester_employee_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "owner_department_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "active_department_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "status",
            request_status_enum,
            server_default=sa.text("'created'"),
            nullable=False,
        ),
        sa.Column(
            "current_stage",
            sa.String(length=100),
            server_default=sa.text("'request_received'"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            request_priority_enum,
            server_default=sa.text("'normal'"),
            nullable=False,
        ),
        sa.Column(
            "workflow_state",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "custom_data",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("final_decision", sa.Text(), nullable=True),
        sa.Column("final_reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('created', 'routing', 'cancelled') "
            "OR owner_department_id IS NOT NULL",
            name="ck_business_requests_owner_for_owned_status",
        ),
        sa.CheckConstraint(
            "active_department_id IS NULL OR owner_department_id IS NOT NULL",
            name="ck_business_requests_active_requires_owner",
        ),
        sa.CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL",
            name="ck_business_requests_completed_timestamp",
        ),
        sa.CheckConstraint(
            "status != 'cancelled' OR cancelled_at IS NOT NULL",
            name="ck_business_requests_cancelled_timestamp",
        ),
        sa.ForeignKeyConstraint(
            ["active_department_id"],
            ["departments.id"],
            name="fk_business_requests_active_department_id_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_business_requests_company_id_companies",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_department_id"],
            ["departments.id"],
            name="fk_business_requests_owner_department_id_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requester_employee_id"],
            ["employees.id"],
            name="fk_business_requests_requester_employee_id_employees",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["users.id"],
            name="fk_business_requests_requester_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_business_requests"),
    )
    op.create_index(
        "ix_business_requests_company_created",
        "business_requests",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_business_requests_company_status",
        "business_requests",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_business_requests_company_requester",
        "business_requests",
        ["company_id", "requester_user_id"],
    )
    op.create_index(
        "ix_business_requests_company_owner",
        "business_requests",
        ["company_id", "owner_department_id"],
    )
    op.create_index(
        "ix_business_requests_company_active",
        "business_requests",
        ["company_id", "active_department_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_business_requests_company_active",
        table_name="business_requests",
    )
    op.drop_index(
        "ix_business_requests_company_owner",
        table_name="business_requests",
    )
    op.drop_index(
        "ix_business_requests_company_requester",
        table_name="business_requests",
    )
    op.drop_index(
        "ix_business_requests_company_status",
        table_name="business_requests",
    )
    op.drop_index(
        "ix_business_requests_company_created",
        table_name="business_requests",
    )
    op.drop_table("business_requests")
    request_priority_enum.drop(op.get_bind(), checkfirst=True)
    request_status_enum.drop(op.get_bind(), checkfirst=True)
