"""Create HR leave, staffing, onboarding, and job-description foundation.

Revision ID: 20260719_0012
Revises: 20260719_0011
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260719_0012"
down_revision: str | Sequence[str] | None = "20260719_0011"
branch_labels = None
depends_on = None

ENUMS = {
    "hr_leave_type": ("annual", "sick", "unpaid", "maternity", "paternity", "bereavement", "study", "other"),
    "hr_eligibility_status": ("pending", "eligible", "ineligible"),
    "hr_balance_status": ("pending", "sufficient", "insufficient", "not_applicable"),
    "hr_staffing_status": ("pending", "satisfied", "conflict", "not_applicable"),
    "hr_approval_status": ("not_required", "pending", "approved", "rejected"),
    "hr_leave_decision": ("pending", "approved", "rejected", "cancelled"),
    "hr_onboarding_status": ("preparing", "waiting_for_it", "in_progress", "completed", "cancelled"),
    "hr_job_description_status": ("draft", "approved", "archived"),
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
    days = sa.Numeric(7, 2)
    op.add_column("employees", sa.Column("hire_date", sa.Date(), nullable=True))

    op.create_table(
        "leave_balances",
        sa.Column("company_id", uuid, nullable=False),
        sa.Column("employee_id", uuid, nullable=False),
        sa.Column("leave_type", enum("hr_leave_type"), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated_days", days, nullable=False),
        sa.Column("used_days", days, server_default="0", nullable=False),
        sa.Column("reserved_days", days, server_default="0", nullable=False),
        sa.Column("remaining_days", days, sa.Computed("allocated_days - used_days - reserved_days", persisted=True)),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False), *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "employee_id", "leave_type", "year", name="uq_leave_balances_employee_type_year"),
        sa.CheckConstraint("allocated_days >= 0 AND used_days >= 0 AND reserved_days >= 0", name="ck_leave_balances_nonnegative"),
        sa.CheckConstraint("used_days + reserved_days <= allocated_days", name="ck_leave_balances_within_allocation"),
    )
    op.create_index("ix_leave_balances_company_employee", "leave_balances", ["company_id", "employee_id"])

    op.create_table(
        "leave_requests",
        sa.Column("request_id", uuid, nullable=False), sa.Column("company_id", uuid, nullable=False),
        sa.Column("employee_id", uuid, nullable=False), sa.Column("leave_type", enum("hr_leave_type"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("requested_days", days, nullable=False), sa.Column("reason", sa.Text()),
        sa.Column("eligibility_status", enum("hr_eligibility_status"), nullable=False),
        sa.Column("balance_status", enum("hr_balance_status"), nullable=False),
        sa.Column("staffing_status", enum("hr_staffing_status"), nullable=False),
        sa.Column("approval_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("approval_status", enum("hr_approval_status"), nullable=False),
        sa.Column("decision", enum("hr_leave_decision"), nullable=False),
        sa.Column("decision_reason", sa.Text()), sa.Column("reserved_days", days, server_default="0", nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)), sa.Column("cancelled_at", sa.DateTime(timezone=True)), *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("request_id"),
        sa.CheckConstraint("end_date >= start_date", name="ck_leave_requests_date_range"),
        sa.CheckConstraint("requested_days > 0 AND reserved_days >= 0 AND reserved_days <= requested_days", name="ck_leave_requests_days"),
    )
    op.create_index("ix_leave_requests_company_employee", "leave_requests", ["company_id", "employee_id"])
    op.create_index("ix_leave_requests_company_dates", "leave_requests", ["company_id", "start_date", "end_date"])

    op.create_table(
        "company_holidays", sa.Column("company_id", uuid, nullable=False), sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False), sa.Column("is_paid", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("id", uuid, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "holiday_date", name="uq_company_holidays_date"),
    )
    op.create_index("ix_company_holidays_company_date", "company_holidays", ["company_id", "holiday_date"])

    op.create_table(
        "department_staffing_rules", sa.Column("company_id", uuid, nullable=False), sa.Column("department_id", uuid, nullable=False),
        sa.Column("minimum_active_employees", sa.Integer(), nullable=False), sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date()), sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False), sa.Column("id", uuid, nullable=False), *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "department_id", "effective_from", name="uq_staffing_rules_department_effective"),
        sa.CheckConstraint("minimum_active_employees >= 0", name="ck_staffing_rules_minimum_nonnegative"),
        sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_staffing_rules_dates"),
    )
    op.create_index("ix_staffing_rules_company_department", "department_staffing_rules", ["company_id", "department_id", "is_active"])

    op.create_table(
        "onboarding_requests", sa.Column("request_id", uuid, nullable=False), sa.Column("company_id", uuid, nullable=False),
        sa.Column("employee_id", uuid, nullable=False), sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("department_id", uuid, nullable=False), sa.Column("manager_employee_id", uuid),
        sa.Column("onboarding_status", enum("hr_onboarding_status"), nullable=False),
        sa.Column("required_actions", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("completed_actions", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("missing_data", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)), *timestamps(),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["manager_employee_id"], ["employees.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index("ix_onboarding_requests_company_id", "onboarding_requests", ["company_id"])

    op.create_table(
        "job_descriptions", sa.Column("company_id", uuid, nullable=False), sa.Column("request_id", uuid),
        sa.Column("title", sa.String(255), nullable=False), sa.Column("department_id", uuid, nullable=False),
        sa.Column("employment_type", sa.String(100), nullable=False), sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("responsibilities", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("required_skills", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("preferred_skills", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("experience_level", sa.String(100), nullable=False),
        sa.Column("education_requirements", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("reporting_to", sa.String(255)), sa.Column("work_location", sa.String(255)),
        sa.Column("status", enum("hr_job_description_status"), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("created_by_user_id", uuid, nullable=False),
        sa.Column("custom_data", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", uuid, nullable=False), *timestamps(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["request_id"], ["business_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_job_descriptions_company_department", "job_descriptions", ["company_id", "department_id"])


def downgrade() -> None:
    op.drop_index("ix_job_descriptions_company_department", table_name="job_descriptions")
    op.drop_table("job_descriptions")
    op.drop_index("ix_onboarding_requests_company_id", table_name="onboarding_requests")
    op.drop_table("onboarding_requests")
    op.drop_index("ix_staffing_rules_company_department", table_name="department_staffing_rules")
    op.drop_table("department_staffing_rules")
    op.drop_index("ix_company_holidays_company_date", table_name="company_holidays")
    op.drop_table("company_holidays")
    op.drop_index("ix_leave_requests_company_dates", table_name="leave_requests")
    op.drop_index("ix_leave_requests_company_employee", table_name="leave_requests")
    op.drop_table("leave_requests")
    op.drop_index("ix_leave_balances_company_employee", table_name="leave_balances")
    op.drop_table("leave_balances")
    op.drop_column("employees", "hire_date")
    bind = op.get_bind()
    for name in reversed(tuple(ENUMS)):
        enum(name).drop(bind, checkfirst=True)
