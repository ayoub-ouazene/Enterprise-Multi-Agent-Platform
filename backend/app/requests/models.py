from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.requests.enums import RequestPriority, RequestStatus

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.departments.models import Department
    from app.employees.models import Employee
    from app.users.models import User


class BusinessRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "business_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created', 'routing', 'cancelled', 'failed') "
            "OR owner_department_id IS NOT NULL",
            name="ck_business_requests_owner_for_owned_status",
        ),
        CheckConstraint(
            "active_department_id IS NULL OR owner_department_id IS NOT NULL",
            name="ck_business_requests_active_requires_owner",
        ),
        CheckConstraint(
            "status != 'completed' OR completed_at IS NOT NULL",
            name="ck_business_requests_completed_timestamp",
        ),
        CheckConstraint(
            "status != 'cancelled' OR cancelled_at IS NOT NULL",
            name="ck_business_requests_cancelled_timestamp",
        ),
        CheckConstraint(
            "status != 'failed' OR failed_at IS NOT NULL",
            name="ck_business_requests_failed_timestamp",
        ),
        Index("ix_business_requests_company_created", "company_id", "created_at"),
        Index("ix_business_requests_company_status", "company_id", "status"),
        Index(
            "ix_business_requests_company_requester",
            "company_id",
            "requester_user_id",
        ),
        Index(
            "ix_business_requests_company_owner",
            "company_id",
            "owner_department_id",
        ),
        Index(
            "ix_business_requests_company_active",
            "company_id",
            "active_department_id",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requester_employee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    active_department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        SAEnum(
            RequestStatus,
            name="request_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=RequestStatus.CREATED,
        server_default=RequestStatus.CREATED.value,
    )
    current_stage: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="request_received",
        server_default="request_received",
    )
    priority: Mapped[RequestPriority] = mapped_column(
        SAEnum(
            RequestPriority,
            name="request_priority",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=RequestPriority.NORMAL,
        server_default=RequestPriority.NORMAL.value,
    )
    workflow_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    custom_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    final_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(
        foreign_keys=[company_id],
        lazy="raise",
    )
    requester_user: Mapped["User"] = relationship(
        foreign_keys=[requester_user_id],
        lazy="raise",
    )
    requester_employee: Mapped["Employee | None"] = relationship(
        foreign_keys=[requester_employee_id],
        lazy="raise",
    )
    owner_department: Mapped["Department | None"] = relationship(
        foreign_keys=[owner_department_id],
        lazy="raise",
    )
    active_department: Mapped["Department | None"] = relationship(
        foreign_keys=[active_department_id],
        lazy="raise",
    )
