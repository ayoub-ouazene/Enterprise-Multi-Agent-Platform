from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.departments.hr.enums import (
    ApprovalStatus,
    BalanceStatus,
    EligibilityStatus,
    JobDescriptionStatus,
    LeaveDecision,
    LeaveType,
    OnboardingStatus,
    StaffingStatus,
)

DAY_PRECISION = 7
DAY_SCALE = 2


class LeaveBalance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leave_balances"
    __table_args__ = (
        UniqueConstraint("company_id", "employee_id", "leave_type", "year", name="uq_leave_balances_employee_type_year"),
        CheckConstraint("allocated_days >= 0 AND used_days >= 0 AND reserved_days >= 0", name="ck_leave_balances_nonnegative"),
        CheckConstraint("used_days + reserved_days <= allocated_days", name="ck_leave_balances_within_allocation"),
        Index("ix_leave_balances_company_employee", "company_id", "employee_id"),
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(SAEnum(LeaveType, name="hr_leave_type", values_callable=enum_values), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_days: Mapped[Decimal] = mapped_column(Numeric(DAY_PRECISION, DAY_SCALE), nullable=False)
    used_days: Mapped[Decimal] = mapped_column(Numeric(DAY_PRECISION, DAY_SCALE), nullable=False, default=Decimal("0.00"), server_default="0")
    reserved_days: Mapped[Decimal] = mapped_column(Numeric(DAY_PRECISION, DAY_SCALE), nullable=False, default=Decimal("0.00"), server_default="0")
    remaining_days: Mapped[Decimal] = mapped_column(
        Numeric(DAY_PRECISION, DAY_SCALE),
        Computed("allocated_days - used_days - reserved_days", persisted=True),
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))

class LeaveRequest(TimestampMixin, Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_leave_requests_date_range"),
        CheckConstraint("requested_days > 0 AND reserved_days >= 0 AND reserved_days <= requested_days", name="ck_leave_requests_days"),
        Index("ix_leave_requests_company_employee", "company_id", "employee_id"),
        Index("ix_leave_requests_company_dates", "company_id", "start_date", "end_date"),
    )
    request_id: Mapped[UUID] = mapped_column(ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    leave_type: Mapped[LeaveType] = mapped_column(SAEnum(LeaveType, name="hr_leave_type", values_callable=enum_values), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_days: Mapped[Decimal] = mapped_column(Numeric(DAY_PRECISION, DAY_SCALE), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    eligibility_status: Mapped[EligibilityStatus] = mapped_column(SAEnum(EligibilityStatus, name="hr_eligibility_status", values_callable=enum_values), nullable=False)
    balance_status: Mapped[BalanceStatus] = mapped_column(SAEnum(BalanceStatus, name="hr_balance_status", values_callable=enum_values), nullable=False)
    staffing_status: Mapped[StaffingStatus] = mapped_column(SAEnum(StaffingStatus, name="hr_staffing_status", values_callable=enum_values), nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    approval_status: Mapped[ApprovalStatus] = mapped_column(SAEnum(ApprovalStatus, name="hr_approval_status", values_callable=enum_values), nullable=False)
    decision: Mapped[LeaveDecision] = mapped_column(SAEnum(LeaveDecision, name="hr_leave_decision", values_callable=enum_values), nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    reserved_days: Mapped[Decimal] = mapped_column(Numeric(DAY_PRECISION, DAY_SCALE), nullable=False, default=Decimal("0.00"), server_default="0")
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompanyHoliday(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "company_holidays"
    __table_args__ = (
        UniqueConstraint("company_id", "holiday_date", name="uq_company_holidays_date"),
        Index("ix_company_holidays_company_date", "company_id", "holiday_date"),
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


class DepartmentStaffingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "department_staffing_rules"
    __table_args__ = (
        UniqueConstraint("company_id", "department_id", "effective_from", name="uq_staffing_rules_department_effective"),
        CheckConstraint("minimum_active_employees >= 0", name="ck_staffing_rules_minimum_nonnegative"),
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_staffing_rules_dates"),
        Index("ix_staffing_rules_company_department", "company_id", "department_id", "is_active"),
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    minimum_active_employees: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))


class OnboardingRequest(TimestampMixin, Base):
    __tablename__ = "onboarding_requests"
    request_id: Mapped[UUID] = mapped_column(ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    manager_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    onboarding_status: Mapped[OnboardingStatus] = mapped_column(SAEnum(OnboardingStatus, name="hr_onboarding_status", values_callable=enum_values), nullable=False)
    required_actions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    completed_actions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    missing_data: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobDescription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (Index("ix_job_descriptions_company_department", "company_id", "department_id"),)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    request_id: Mapped[UUID | None] = mapped_column(ForeignKey("business_requests.id", ondelete="SET NULL"), unique=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    employment_type: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    required_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    preferred_skills: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    experience_level: Mapped[str] = mapped_column(String(100), nullable=False)
    education_requirements: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    reporting_to: Mapped[str | None] = mapped_column(String(255))
    work_location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[JobDescriptionStatus] = mapped_column(SAEnum(JobDescriptionStatus, name="hr_job_description_status", values_callable=enum_values), nullable=False, default=JobDescriptionStatus.DRAFT, server_default=JobDescriptionStatus.DRAFT.value)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
