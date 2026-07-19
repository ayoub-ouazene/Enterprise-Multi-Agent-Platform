"""Create the Customer Support request extension.

Revision ID: 20260719_0008
Revises: 20260719_0007
Create Date: 2026-07-19
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260719_0008"
down_revision: str | Sequence[str] | None = "20260719_0007"
branch_labels = None
depends_on = None

category = postgresql.ENUM(
    "faq", "product_information", "service_information", "policy_explanation",
    "troubleshooting", "technical_issue", "human_escalation", "unsupported",
    name="customer_support_category", create_type=False,
)
issue_status = postgresql.ENUM(
    "new", "diagnosing", "waiting_for_customer", "waiting_for_it",
    "waiting_for_human_support", "resolved", "closed", "failed",
    name="support_issue_status", create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    category.create(bind, checkfirst=True)
    issue_status.create(bind, checkfirst=True)
    op.create_table(
        "support_issues",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("product_or_service", sa.String(255)),
        sa.Column("issue_summary", sa.Text(), nullable=False),
        sa.Column("symptoms", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("error_messages", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("troubleshooting_steps", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("resolution_summary", sa.Text()),
        sa.Column("issue_status", issue_status, server_default=sa.text("'new'"), nullable=False),
        sa.Column("requires_it", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("requires_human_support", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("customer_impact", sa.Text()),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id"),
    )
    for name, columns in (
        ("ix_support_issues_company_status", ["company_id", "issue_status"]),
        ("ix_support_issues_company_category", ["company_id", "category"]),
        ("ix_support_issues_company_it", ["company_id", "requires_it"]),
        ("ix_support_issues_company_human", ["company_id", "requires_human_support"]),
        ("ix_support_issues_company_updated", ["company_id", "updated_at"]),
    ):
        op.create_index(name, "support_issues", columns)


def downgrade() -> None:
    for name in (
        "ix_support_issues_company_updated", "ix_support_issues_company_human",
        "ix_support_issues_company_it", "ix_support_issues_company_category",
        "ix_support_issues_company_status",
    ):
        op.drop_index(name, table_name="support_issues")
    op.drop_table("support_issues")
    issue_status.drop(op.get_bind(), checkfirst=True)
    category.drop(op.get_bind(), checkfirst=True)
