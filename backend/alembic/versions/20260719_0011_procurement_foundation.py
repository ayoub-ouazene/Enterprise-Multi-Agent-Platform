"""Create Procurement request extensions and supplier candidates.

Revision ID: 20260719_0011
Revises: 20260719_0010
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260719_0011"
down_revision: str | Sequence[str] | None = "20260719_0010"
branch_labels = None
depends_on = None


ENUMS = {
    "procurement_request_category": (
        "procurement_information",
        "supplier_search",
        "supplier_evaluation",
        "quotation_comparison",
        "purchase_requirement",
        "shortlist_generation",
        "finance_validation",
        "human_selection_required",
        "unsupported",
    ),
    "procurement_finance_validation_status": (
        "not_required",
        "pending",
        "approved",
        "rejected",
        "approval_required",
    ),
    "procurement_shortlist_status": (
        "pending",
        "generated",
        "no_eligible_candidates",
    ),
    "procurement_selection_status": (
        "not_required",
        "pending",
        "selected",
        "rejected",
    ),
    "supplier_compliance_status": (
        "pending",
        "eligible",
        "ineligible",
        "requires_review",
    ),
    "supplier_availability_status": (
        "unknown",
        "available",
        "limited",
        "unavailable",
    ),
    "supplier_candidate_source_type": (
        "company_catalog",
        "manual_entry",
        "previous_supplier",
        "department_submission",
        "imported",
        "other",
    ),
}


def enum(name: str):
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for name in ENUMS:
        enum(name).create(bind, checkfirst=True)
    uuid = postgresql.UUID(as_uuid=True)
    money = sa.Numeric(18, 2)
    quantity = sa.Numeric(12, 3)
    score = sa.Numeric(6, 3)

    op.create_table(
        "procurement_requests",
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("requesting_department_id", uuid),
        sa.Column("category", enum("procurement_request_category"), nullable=False),
        sa.Column("item_or_service", sa.String(500), nullable=False),
        sa.Column("quantity", quantity, nullable=False),
        sa.Column(
            "minimum_specifications",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "required_certifications",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("delivery_location", sa.String(500)),
        sa.Column("required_by_date", sa.Date()),
        sa.Column("estimated_budget", money),
        sa.Column("approved_budget", money),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column(
            "evaluation_criteria",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "finance_validation_status",
            enum("procurement_finance_validation_status"),
            server_default=sa.text("'not_required'"),
            nullable=False,
        ),
        sa.Column(
            "shortlist_status",
            enum("procurement_shortlist_status"),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("selected_candidate_id", uuid),
        sa.Column(
            "selection_status",
            enum("procurement_selection_status"),
            server_default=sa.text("'not_required'"),
            nullable=False,
        ),
        sa.Column(
            "custom_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(
            ["request_id"], ["business_requests.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requesting_department_id"], ["departments.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("request_id"),
        sa.CheckConstraint(
            "quantity > 0", name="ck_procurement_requests_quantity_positive"
        ),
        sa.CheckConstraint(
            "estimated_budget IS NULL OR estimated_budget >= 0",
            name="ck_procurement_requests_estimated_budget_nonnegative",
        ),
        sa.CheckConstraint(
            "approved_budget IS NULL OR approved_budget >= 0",
            name="ck_procurement_requests_approved_budget_nonnegative",
        ),
    )
    op.create_index(
        "ix_procurement_requests_company_category",
        "procurement_requests",
        ["company_id", "category"],
    )
    op.create_index(
        "ix_procurement_requests_company_finance",
        "procurement_requests",
        ["company_id", "finance_validation_status"],
    )
    op.create_index(
        "ix_procurement_requests_company_selection",
        "procurement_requests",
        ["company_id", "selection_status"],
    )

    op.create_table(
        "supplier_candidates",
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("request_id", uuid, nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("supplier_reference", sa.String(255)),
        sa.Column("contact_reference", sa.String(255)),
        sa.Column("item_or_service", sa.String(500), nullable=False),
        sa.Column("quoted_unit_price", money, nullable=False),
        sa.Column("quantity", quantity, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("delivery_cost", money, server_default=sa.text("0.00"), nullable=False),
        sa.Column("tax_amount", money),
        sa.Column("total_cost", money, nullable=False),
        sa.Column("delivery_days", sa.Integer()),
        sa.Column("warranty_months", sa.Integer()),
        sa.Column(
            "meets_minimum_specification",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("compliance_status", enum("supplier_compliance_status"), nullable=False),
        sa.Column("availability_status", enum("supplier_availability_status"), nullable=False),
        sa.Column("quality_score", score),
        sa.Column("price_score", score),
        sa.Column("delivery_score", score),
        sa.Column("compliance_score", score),
        sa.Column("overall_score", score),
        sa.Column("rank", sa.Integer()),
        sa.Column("evaluation_reason", sa.Text()),
        sa.Column("is_shortlisted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_type", enum("supplier_candidate_source_type"), nullable=False),
        sa.Column(
            "custom_data",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", uuid, nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["request_id"], ["procurement_requests.request_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "request_id",
            "supplier_name",
            "item_or_service",
            name="uq_supplier_candidates_request_supplier_item",
        ),
        sa.UniqueConstraint(
            "company_id",
            "request_id",
            "id",
            name="uq_supplier_candidates_company_request_id",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_supplier_candidates_quantity_positive"),
        sa.CheckConstraint(
            "quoted_unit_price >= 0 AND delivery_cost >= 0 AND "
            "(tax_amount IS NULL OR tax_amount >= 0) AND total_cost > 0",
            name="ck_supplier_candidates_money_nonnegative",
        ),
        sa.CheckConstraint(
            "delivery_days IS NULL OR delivery_days >= 0",
            name="ck_supplier_candidates_delivery_nonnegative",
        ),
        sa.CheckConstraint(
            "warranty_months IS NULL OR warranty_months >= 0",
            name="ck_supplier_candidates_warranty_nonnegative",
        ),
        sa.CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_quality_score",
        ),
        sa.CheckConstraint(
            "price_score IS NULL OR price_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_price_score",
        ),
        sa.CheckConstraint(
            "delivery_score IS NULL OR delivery_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_delivery_score",
        ),
        sa.CheckConstraint(
            "compliance_score IS NULL OR compliance_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_compliance_score",
        ),
        sa.CheckConstraint(
            "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_overall_score",
        ),
        sa.CheckConstraint("rank IS NULL OR rank > 0", name="ck_supplier_candidates_rank"),
    )
    op.create_index(
        "ix_supplier_candidates_company_request",
        "supplier_candidates",
        ["company_id", "request_id"],
    )
    op.create_index(
        "ix_supplier_candidates_request_rank",
        "supplier_candidates",
        ["company_id", "request_id", "rank"],
    )
    op.create_index(
        "ix_supplier_candidates_request_shortlist",
        "supplier_candidates",
        ["company_id", "request_id", "is_shortlisted"],
    )
    op.create_index(
        "uq_supplier_candidates_one_selected",
        "supplier_candidates",
        ["company_id", "request_id"],
        unique=True,
        postgresql_where=sa.text("is_selected"),
    )
    op.create_foreign_key(
        "fk_procurement_requests_selected_candidate",
        "procurement_requests",
        "supplier_candidates",
        ["selected_candidate_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_procurement_requests_selected_candidate",
        "procurement_requests",
        type_="foreignkey",
    )
    for index in (
        "uq_supplier_candidates_one_selected",
        "ix_supplier_candidates_request_shortlist",
        "ix_supplier_candidates_request_rank",
        "ix_supplier_candidates_company_request",
    ):
        op.drop_index(index, table_name="supplier_candidates")
    op.drop_table("supplier_candidates")
    for index in (
        "ix_procurement_requests_company_selection",
        "ix_procurement_requests_company_finance",
        "ix_procurement_requests_company_category",
    ):
        op.drop_index(index, table_name="procurement_requests")
    op.drop_table("procurement_requests")
    bind = op.get_bind()
    for name in reversed(tuple(ENUMS)):
        enum(name).drop(bind, checkfirst=True)
