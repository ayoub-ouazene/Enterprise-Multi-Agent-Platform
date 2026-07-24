from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
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

from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.requests.models import BusinessRequest
    from app.users.models import User


class HumanAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "human_actions"
    __table_args__ = (
        Index(
            "ix_human_actions_company_status",
            "company_id",
            "status",
        ),
        Index(
            "ix_human_actions_company_due",
            "company_id",
            "due_date",
        ),
        Index(
            "ix_human_actions_request",
            "request_id",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("business_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(
            "pending",
            "resolved",
            "cancelled",
            name="human_action_status",
        ),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    assigned_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_role: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    decision_package: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    response: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(
        foreign_keys=[company_id],
        lazy="raise",
    )
    request: Mapped["BusinessRequest"] = relationship(
        foreign_keys=[request_id],
        lazy="raise",
    )
    assigned_user: Mapped["User | None"] = relationship(
        foreign_keys=[assigned_user_id],
        lazy="raise",
    )
