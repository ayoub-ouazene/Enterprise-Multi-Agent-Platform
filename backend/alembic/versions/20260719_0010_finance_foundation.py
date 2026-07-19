"""Create Finance budgets, request extensions, and financial transactions.

Revision ID: 20260719_0010
Revises: 20260719_0009
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260719_0010"
down_revision: str | Sequence[str] | None = "20260719_0009"
branch_labels = None
depends_on = None


ENUMS = {
    "budget_type": ("company", "department", "project", "operational", "capital"),
    "budget_status": ("draft", "active", "frozen", "closed"),
    "finance_request_category": (
        "finance_information", "budget_inquiry", "budget_validation",
        "purchase_validation", "expense_policy", "budget_reservation",
        "transaction_confirmation", "it_purchase_validation",
        "procurement_purchase_validation", "human_approval_required", "unsupported",
    ),
    "finance_approval_status": ("not_required", "pending", "approved", "rejected"),
    "finance_reservation_status": ("not_requested", "pending", "reserved", "released", "failed"),
    "finance_decision": (
        "answer", "validated", "rejected", "approval_required", "reserved",
        "released", "transaction_recorded", "clarify", "return_to_it",
        "return_to_procurement", "use_tool", "unsupported",
    ),
    "financial_transaction_type": (
        "reservation", "commitment", "expense", "release", "adjustment", "reversal",
    ),
    "financial_transaction_status": ("pending", "confirmed", "rejected", "reversed"),
}


def enum(name: str):
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for name in ENUMS:
        enum(name).create(bind, checkfirst=True)
    uuid = postgresql.UUID(as_uuid=True)
    money = sa.Numeric(18, 2)

    op.create_table(
        "budgets",
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("department_id", uuid),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("budget_type", enum("budget_type"), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("allocated_amount", money, nullable=False),
        sa.Column("reserved_amount", money, server_default=sa.text("0.00"), nullable=False),
        sa.Column("committed_amount", money, server_default=sa.text("0.00"), nullable=False),
        sa.Column("spent_amount", money, server_default=sa.text("0.00"), nullable=False),
        sa.Column("status", enum("budget_status"), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("approval_threshold", money),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", "period_start", "period_end", name="uq_budgets_company_name_period"),
        sa.CheckConstraint("period_end >= period_start", name="ck_budgets_period"),
        sa.CheckConstraint("allocated_amount >= 0", name="ck_budgets_allocated_nonnegative"),
        sa.CheckConstraint("reserved_amount >= 0", name="ck_budgets_reserved_nonnegative"),
        sa.CheckConstraint("committed_amount >= 0", name="ck_budgets_committed_nonnegative"),
        sa.CheckConstraint("spent_amount >= 0", name="ck_budgets_spent_nonnegative"),
        sa.CheckConstraint("approval_threshold IS NULL OR approval_threshold >= 0", name="ck_budgets_threshold_nonnegative"),
    )
    op.create_index("ix_budgets_company_status_period", "budgets", ["company_id", "status", "period_start", "period_end"])
    op.create_index("ix_budgets_company_department", "budgets", ["company_id", "department_id"])

    op.create_table(
        "finance_requests",
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("requesting_department_id", uuid),
        sa.Column("budget_id", uuid),
        sa.Column("category", enum("finance_request_category"), nullable=False),
        sa.Column("requested_amount", money),
        sa.Column("currency", sa.String(3)),
        sa.Column("business_reason", sa.Text(), nullable=False),
        sa.Column("cost_center", sa.String(100)),
        sa.Column("available_budget", money),
        sa.Column("budget_sufficient", sa.Boolean()),
        sa.Column("policy_compliant", sa.Boolean()),
        sa.Column("approval_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approval_status", enum("finance_approval_status"), server_default=sa.text("'not_required'"), nullable=False),
        sa.Column("reservation_status", enum("finance_reservation_status"), server_default=sa.text("'not_requested'"), nullable=False),
        sa.Column("decision", enum("finance_decision"), nullable=False),
        sa.Column("decision_reason", sa.Text(), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requesting_department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("request_id"),
        sa.CheckConstraint("requested_amount IS NULL OR requested_amount > 0", name="ck_finance_requests_amount_positive"),
    )
    op.create_index("ix_finance_requests_company_budget", "finance_requests", ["company_id", "budget_id"])
    op.create_index("ix_finance_requests_company_approval", "finance_requests", ["company_id", "approval_status"])

    op.create_table(
        "financial_transactions",
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("request_id", uuid),
        sa.Column("budget_id", uuid, nullable=False),
        sa.Column("transaction_type", enum("financial_transaction_type"), nullable=False),
        sa.Column("amount", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", enum("financial_transaction_status"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("created_by_user_id", uuid, nullable=False),
        sa.Column("approved_by_user_id", uuid),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("reversed_transaction_id", uuid),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["budget_id"], ["budgets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reversed_transaction_id"], ["financial_transactions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "reference", name="uq_financial_transactions_company_reference"),
        sa.CheckConstraint("amount > 0", name="ck_financial_transactions_amount_positive"),
    )
    op.create_index("ix_financial_transactions_company_budget", "financial_transactions", ["company_id", "budget_id"])
    op.create_index("ix_financial_transactions_company_request", "financial_transactions", ["company_id", "request_id"])
    op.create_index("ix_financial_transactions_company_status", "financial_transactions", ["company_id", "status"])


def downgrade() -> None:
    for index in (
        "ix_financial_transactions_company_status",
        "ix_financial_transactions_company_request",
        "ix_financial_transactions_company_budget",
    ):
        op.drop_index(index, table_name="financial_transactions")
    op.drop_table("financial_transactions")
    for index in ("ix_finance_requests_company_approval", "ix_finance_requests_company_budget"):
        op.drop_index(index, table_name="finance_requests")
    op.drop_table("finance_requests")
    for index in ("ix_budgets_company_department", "ix_budgets_company_status_period"):
        op.drop_index(index, table_name="budgets")
    op.drop_table("budgets")
    bind = op.get_bind()
    for name in reversed(tuple(ENUMS)):
        enum(name).drop(bind, checkfirst=True)
