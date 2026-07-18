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
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin
from app.notifications.enums import (
    NotificationActionType,
    NotificationSeverity,
    NotificationType,
)

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.requests.models import BusinessRequest
    from app.users.models import User


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "NOT action_required OR action_type IS NOT NULL",
            name="ck_notifications_required_action_type",
        ),
        CheckConstraint(
            "(is_read AND read_at IS NOT NULL) OR (NOT is_read AND read_at IS NULL)",
            name="ck_notifications_read_timestamp",
        ),
        Index(
            "ix_notifications_company_recipient_created",
            "company_id",
            "recipient_user_id",
            "created_at",
        ),
        Index(
            "ix_notifications_company_recipient_read",
            "company_id",
            "recipient_user_id",
            "is_read",
        ),
        Index(
            "ix_notifications_company_request",
            "company_id",
            "request_id",
        ),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("business_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(
            NotificationType,
            name="notification_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[NotificationSeverity] = mapped_column(
        SAEnum(
            NotificationSeverity,
            name="notification_severity",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=NotificationSeverity.INFO,
        server_default=NotificationSeverity.INFO.value,
    )
    action_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    action_type: Mapped[NotificationActionType | None] = mapped_column(
        SAEnum(
            NotificationActionType,
            name="notification_action_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=True,
    )
    action_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    notification_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(
        foreign_keys=[company_id],
        lazy="raise",
    )
    recipient: Mapped["User"] = relationship(
        foreign_keys=[recipient_user_id],
        lazy="raise",
    )
    business_request: Mapped["BusinessRequest | None"] = relationship(
        foreign_keys=[request_id],
        lazy="raise",
    )
