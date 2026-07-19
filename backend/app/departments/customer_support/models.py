from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.departments.customer_support.enums import CustomerSupportCategory, SupportIssueStatus

if TYPE_CHECKING:
    from app.requests.models import BusinessRequest


class SupportIssue(TimestampMixin, Base):
    __tablename__ = "support_issues"
    __table_args__ = (
        Index("ix_support_issues_company_status", "company_id", "issue_status"),
        Index("ix_support_issues_company_category", "company_id", "category"),
        Index("ix_support_issues_company_it", "company_id", "requires_it"),
        Index("ix_support_issues_company_human", "company_id", "requires_human_support"),
        Index("ix_support_issues_company_updated", "company_id", "updated_at"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_requests.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[CustomerSupportCategory] = mapped_column(
        SAEnum(CustomerSupportCategory, name="customer_support_category", values_callable=enum_values),
        nullable=False,
    )
    product_or_service: Mapped[str | None] = mapped_column(String(255))
    issue_summary: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    error_messages: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    troubleshooting_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    issue_status: Mapped[SupportIssueStatus] = mapped_column(
        SAEnum(SupportIssueStatus, name="support_issue_status", values_callable=enum_values),
        nullable=False, default=SupportIssueStatus.NEW, server_default=SupportIssueStatus.NEW.value,
    )
    requires_it: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    requires_human_support: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    customer_impact: Mapped[str | None] = mapped_column(Text)
    custom_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    business_request: Mapped["BusinessRequest"] = relationship(lazy="raise")
