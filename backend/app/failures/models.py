from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.failures.enums import CapabilityGapStatus, FailureSource, FailureType

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.departments.models import Department
    from app.requests.models import BusinessRequest
    from app.users.models import User


class FailureLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "failure_logs"
    __table_args__ = (
        CheckConstraint(
            "resolved OR (resolved_at IS NULL AND resolved_by_user_id IS NULL)",
            name="ck_failure_logs_unresolved_fields",
        ),
        Index("ix_failure_logs_company_request", "company_id", "request_id"),
        Index("ix_failure_logs_company_department", "company_id", "department_id"),
        Index("ix_failure_logs_company_type", "company_id", "failure_type"),
        Index("ix_failure_logs_company_created", "company_id", "created_at"),
        Index("ix_failure_logs_company_resolved", "company_id", "resolved"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_requests.id", ondelete="SET NULL")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    failure_type: Mapped[FailureType] = mapped_column(
        SAEnum(
            FailureType,
            name="failure_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    failure_source: Mapped[FailureSource] = mapped_column(
        SAEnum(
            FailureSource,
            name="failure_source",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    failed_operation: Mapped[str] = mapped_column(String(255), nullable=False)
    internal_message: Mapped[str] = mapped_column(Text, nullable=False)
    safe_message: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    technical_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    alternative_attempted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    alternative_description: Mapped[str | None] = mapped_column(Text)
    is_terminal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    company: Mapped["Company"] = relationship(foreign_keys=[company_id], lazy="raise")
    business_request: Mapped["BusinessRequest | None"] = relationship(
        foreign_keys=[request_id], lazy="raise"
    )
    department: Mapped["Department | None"] = relationship(
        foreign_keys=[department_id], lazy="raise"
    )
    resolved_by: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by_user_id], lazy="raise"
    )


class CapabilityGap(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "capability_gaps"
    __table_args__ = (
        CheckConstraint(
            "occurrence_count > 0", name="ck_capability_gaps_positive_occurrences"
        ),
        Index("ix_capability_gaps_company_status", "company_id", "status"),
        Index("ix_capability_gaps_company_department", "company_id", "department_id"),
        Index("ix_capability_gaps_company_last_seen", "company_id", "last_seen_at"),
        Index(
            "uq_capability_gaps_unresolved_dedup",
            "company_id",
            "deduplication_key",
            unique=True,
            postgresql_where=text("status IN ('open', 'acknowledged', 'planned')"),
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_requests.id", ondelete="SET NULL")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL")
    )
    requested_operation: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_operation: Mapped[str] = mapped_column(String(255), nullable=False)
    deduplication_key: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    safe_user_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CapabilityGapStatus] = mapped_column(
        SAEnum(
            CapabilityGapStatus,
            name="capability_gap_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=CapabilityGapStatus.OPEN,
        server_default=CapabilityGapStatus.OPEN.value,
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    gap_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    company: Mapped["Company"] = relationship(foreign_keys=[company_id], lazy="raise")
    business_request: Mapped["BusinessRequest | None"] = relationship(
        foreign_keys=[request_id], lazy="raise"
    )
    department: Mapped["Department | None"] = relationship(
        foreign_keys=[department_id], lazy="raise"
    )
    resolved_by: Mapped["User | None"] = relationship(
        foreign_keys=[resolved_by_user_id], lazy="raise"
    )
