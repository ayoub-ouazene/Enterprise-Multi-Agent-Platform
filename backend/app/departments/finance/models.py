from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.departments.finance.enums import (
    BudgetStatus,
    BudgetType,
    FinanceApprovalStatus,
    FinanceDecision,
    FinanceRequestCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    ReservationStatus,
)


MONEY_PRECISION = 18
MONEY_SCALE = 2


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("period_end >= period_start", name="ck_budgets_period"),
        CheckConstraint("allocated_amount >= 0", name="ck_budgets_allocated_nonnegative"),
        CheckConstraint("reserved_amount >= 0", name="ck_budgets_reserved_nonnegative"),
        CheckConstraint("committed_amount >= 0", name="ck_budgets_committed_nonnegative"),
        CheckConstraint("spent_amount >= 0", name="ck_budgets_spent_nonnegative"),
        CheckConstraint(
            "approval_threshold IS NULL OR approval_threshold >= 0",
            name="ck_budgets_threshold_nonnegative",
        ),
        UniqueConstraint(
            "company_id", "name", "period_start", "period_end",
            name="uq_budgets_company_name_period",
        ),
        Index("ix_budgets_company_status_period", "company_id", "status", "period_start", "period_end"),
        Index("ix_budgets_company_department", "company_id", "department_id"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_type: Mapped[BudgetType] = mapped_column(
        SAEnum(BudgetType, name="budget_type", values_callable=enum_values), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False
    )
    reserved_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False, default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    committed_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False, default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    spent_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False, default=Decimal("0.00"),
        server_default=text("0.00"),
    )
    status: Mapped[BudgetStatus] = mapped_column(
        SAEnum(BudgetStatus, name="budget_status", values_callable=enum_values),
        nullable=False, default=BudgetStatus.DRAFT, server_default=BudgetStatus.DRAFT.value,
    )
    approval_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=text("1"))
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )

    @property
    def available_amount(self) -> Decimal:
        return (
            self.allocated_amount
            - self.reserved_amount
            - self.committed_amount
            - self.spent_amount
        )


class FinanceRequest(TimestampMixin, Base):
    __tablename__ = "finance_requests"
    __table_args__ = (
        CheckConstraint(
            "requested_amount IS NULL OR requested_amount > 0",
            name="ck_finance_requests_amount_positive",
        ),
        Index("ix_finance_requests_company_budget", "company_id", "budget_id"),
        Index("ix_finance_requests_company_approval", "company_id", "approval_status"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    requesting_department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    budget_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("budgets.id", ondelete="SET NULL")
    )
    category: Mapped[FinanceRequestCategory] = mapped_column(
        SAEnum(FinanceRequestCategory, name="finance_request_category", values_callable=enum_values),
        nullable=False,
    )
    requested_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    currency: Mapped[str | None] = mapped_column(String(3))
    business_reason: Mapped[str] = mapped_column(Text, nullable=False)
    cost_center: Mapped[str | None] = mapped_column(String(100))
    available_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    budget_sufficient: Mapped[bool | None] = mapped_column(Boolean)
    policy_compliant: Mapped[bool | None] = mapped_column(Boolean)
    approval_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    approval_status: Mapped[FinanceApprovalStatus] = mapped_column(
        SAEnum(FinanceApprovalStatus, name="finance_approval_status", values_callable=enum_values),
        nullable=False, default=FinanceApprovalStatus.NOT_REQUIRED,
        server_default=FinanceApprovalStatus.NOT_REQUIRED.value,
    )
    reservation_status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, name="finance_reservation_status", values_callable=enum_values),
        nullable=False, default=ReservationStatus.NOT_REQUESTED,
        server_default=ReservationStatus.NOT_REQUESTED.value,
    )
    decision: Mapped[FinanceDecision] = mapped_column(
        SAEnum(FinanceDecision, name="finance_decision", values_callable=enum_values),
        nullable=False,
    )
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinancialTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "financial_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_financial_transactions_amount_positive"),
        UniqueConstraint(
            "company_id", "reference", name="uq_financial_transactions_company_reference"
        ),
        Index("ix_financial_transactions_company_budget", "company_id", "budget_id"),
        Index("ix_financial_transactions_company_request", "company_id", "request_id"),
        Index("ix_financial_transactions_company_status", "company_id", "status"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_requests.id", ondelete="SET NULL")
    )
    budget_id: Mapped[UUID] = mapped_column(
        ForeignKey("budgets.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_type: Mapped[FinancialTransactionType] = mapped_column(
        SAEnum(
            FinancialTransactionType,
            name="financial_transaction_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[FinancialTransactionStatus] = mapped_column(
        SAEnum(
            FinancialTransactionStatus,
            name="financial_transaction_status",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversed_transaction_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("financial_transactions.id", ondelete="RESTRICT")
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
