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
from app.departments.procurement.enums import (
    AvailabilityStatus,
    CandidateSourceType,
    ComplianceStatus,
    FinanceValidationStatus,
    ProcurementRequestCategory,
    SelectionStatus,
    ShortlistStatus,
)


MONEY_PRECISION = 18
MONEY_SCALE = 2
QUANTITY_PRECISION = 12
QUANTITY_SCALE = 3
SCORE_PRECISION = 6
SCORE_SCALE = 3


class ProcurementRequest(TimestampMixin, Base):
    __tablename__ = "procurement_requests"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_procurement_requests_quantity_positive"),
        CheckConstraint(
            "estimated_budget IS NULL OR estimated_budget >= 0",
            name="ck_procurement_requests_estimated_budget_nonnegative",
        ),
        CheckConstraint(
            "approved_budget IS NULL OR approved_budget >= 0",
            name="ck_procurement_requests_approved_budget_nonnegative",
        ),
        Index("ix_procurement_requests_company_category", "company_id", "category"),
        Index(
            "ix_procurement_requests_company_finance",
            "company_id",
            "finance_validation_status",
        ),
        Index(
            "ix_procurement_requests_company_selection",
            "company_id",
            "selection_status",
        ),
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
    category: Mapped[ProcurementRequestCategory] = mapped_column(
        SAEnum(
            ProcurementRequestCategory,
            name="procurement_request_category",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    item_or_service: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    minimum_specifications: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    required_certifications: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    delivery_location: Mapped[str | None] = mapped_column(String(500))
    required_by_date: Mapped[date | None] = mapped_column(Date)
    estimated_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    approved_budget: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    evaluation_criteria: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    finance_validation_status: Mapped[FinanceValidationStatus] = mapped_column(
        SAEnum(
            FinanceValidationStatus,
            name="procurement_finance_validation_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=FinanceValidationStatus.NOT_REQUIRED,
        server_default=FinanceValidationStatus.NOT_REQUIRED.value,
    )
    shortlist_status: Mapped[ShortlistStatus] = mapped_column(
        SAEnum(
            ShortlistStatus,
            name="procurement_shortlist_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=ShortlistStatus.PENDING,
        server_default=ShortlistStatus.PENDING.value,
    )
    selected_candidate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "supplier_candidates.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_procurement_requests_selected_candidate",
        ),
        nullable=True,
    )
    selection_status: Mapped[SelectionStatus] = mapped_column(
        SAEnum(
            SelectionStatus,
            name="procurement_selection_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=SelectionStatus.NOT_REQUIRED,
        server_default=SelectionStatus.NOT_REQUIRED.value,
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SupplierCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "supplier_candidates"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_supplier_candidates_quantity_positive"),
        CheckConstraint(
            "quoted_unit_price >= 0 AND delivery_cost >= 0 AND "
            "(tax_amount IS NULL OR tax_amount >= 0) AND total_cost > 0",
            name="ck_supplier_candidates_money_nonnegative",
        ),
        CheckConstraint(
            "delivery_days IS NULL OR delivery_days >= 0",
            name="ck_supplier_candidates_delivery_nonnegative",
        ),
        CheckConstraint(
            "warranty_months IS NULL OR warranty_months >= 0",
            name="ck_supplier_candidates_warranty_nonnegative",
        ),
        CheckConstraint(
            "quality_score IS NULL OR quality_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_quality_score",
        ),
        CheckConstraint(
            "price_score IS NULL OR price_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_price_score",
        ),
        CheckConstraint(
            "delivery_score IS NULL OR delivery_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_delivery_score",
        ),
        CheckConstraint(
            "compliance_score IS NULL OR compliance_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_compliance_score",
        ),
        CheckConstraint(
            "overall_score IS NULL OR overall_score BETWEEN 0 AND 100",
            name="ck_supplier_candidates_overall_score",
        ),
        CheckConstraint("rank IS NULL OR rank > 0", name="ck_supplier_candidates_rank"),
        UniqueConstraint(
            "company_id",
            "request_id",
            "supplier_name",
            "item_or_service",
            name="uq_supplier_candidates_request_supplier_item",
        ),
        UniqueConstraint(
            "company_id",
            "request_id",
            "id",
            name="uq_supplier_candidates_company_request_id",
        ),
        Index("ix_supplier_candidates_company_request", "company_id", "request_id"),
        Index(
            "ix_supplier_candidates_request_rank",
            "company_id",
            "request_id",
            "rank",
        ),
        Index(
            "ix_supplier_candidates_request_shortlist",
            "company_id",
            "request_id",
            "is_shortlisted",
        ),
        Index(
            "uq_supplier_candidates_one_selected",
            "company_id",
            "request_id",
            unique=True,
            postgresql_where=text("is_selected"),
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("procurement_requests.request_id", ondelete="CASCADE"), nullable=False
    )
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_reference: Mapped[str | None] = mapped_column(String(255))
    contact_reference: Mapped[str | None] = mapped_column(String(255))
    item_or_service: Mapped[str] = mapped_column(String(500), nullable=False)
    quoted_unit_price: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(QUANTITY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    delivery_cost: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False, default=Decimal("0.00")
    )
    tax_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE)
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False
    )
    delivery_days: Mapped[int | None] = mapped_column()
    warranty_months: Mapped[int | None] = mapped_column()
    meets_minimum_specification: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    compliance_status: Mapped[ComplianceStatus] = mapped_column(
        SAEnum(
            ComplianceStatus,
            name="supplier_compliance_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=ComplianceStatus.PENDING,
        server_default=ComplianceStatus.PENDING.value,
    )
    availability_status: Mapped[AvailabilityStatus] = mapped_column(
        SAEnum(
            AvailabilityStatus,
            name="supplier_availability_status",
            values_callable=enum_values,
        ),
        nullable=False,
        default=AvailabilityStatus.UNKNOWN,
        server_default=AvailabilityStatus.UNKNOWN.value,
    )
    quality_score: Mapped[Decimal | None] = mapped_column(
        Numeric(SCORE_PRECISION, SCORE_SCALE)
    )
    price_score: Mapped[Decimal | None] = mapped_column(
        Numeric(SCORE_PRECISION, SCORE_SCALE)
    )
    delivery_score: Mapped[Decimal | None] = mapped_column(
        Numeric(SCORE_PRECISION, SCORE_SCALE)
    )
    compliance_score: Mapped[Decimal | None] = mapped_column(
        Numeric(SCORE_PRECISION, SCORE_SCALE)
    )
    overall_score: Mapped[Decimal | None] = mapped_column(
        Numeric(SCORE_PRECISION, SCORE_SCALE)
    )
    rank: Mapped[int | None] = mapped_column()
    evaluation_reason: Mapped[str | None] = mapped_column(Text)
    is_shortlisted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    source_type: Mapped[CandidateSourceType] = mapped_column(
        SAEnum(
            CandidateSourceType,
            name="supplier_candidate_source_type",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
