from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event as sqlalchemy_event,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import UUIDPrimaryKeyMixin
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.departments.models import Department
    from app.requests.models import BusinessRequest
    from app.users.models import User


class AppendOnlyWorkflowEventError(RuntimeError):
    pass


class WorkflowEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        CheckConstraint(
            "sequence_number > 0",
            name="ck_workflow_events_positive_sequence",
        ),
        UniqueConstraint(
            "request_id",
            "sequence_number",
            name="uq_workflow_events_request_sequence",
        ),
        Index(
            "ix_workflow_events_company_request_sequence",
            "company_id",
            "request_id",
            "sequence_number",
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
    event_type: Mapped[WorkflowEventType] = mapped_column(
        SAEnum(
            WorkflowEventType,
            name="workflow_event_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actor_type: Mapped[WorkflowEventActorType] = mapped_column(
        SAEnum(
            WorkflowEventActorType,
            name="workflow_event_actor_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    visibility: Mapped[WorkflowEventVisibility] = mapped_column(
        SAEnum(
            WorkflowEventVisibility,
            name="workflow_event_visibility",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    event_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    company: Mapped["Company"] = relationship(
        foreign_keys=[company_id],
        lazy="raise",
    )
    business_request: Mapped["BusinessRequest"] = relationship(
        foreign_keys=[request_id],
        lazy="raise",
    )
    actor_user: Mapped["User | None"] = relationship(
        foreign_keys=[actor_user_id],
        lazy="raise",
    )
    department: Mapped["Department | None"] = relationship(
        foreign_keys=[department_id],
        lazy="raise",
    )


@sqlalchemy_event.listens_for(WorkflowEvent, "before_update", propagate=True)
def _prevent_workflow_event_update(*_: object) -> None:
    raise AppendOnlyWorkflowEventError("Workflow events are append-only")


@sqlalchemy_event.listens_for(WorkflowEvent, "before_delete", propagate=True)
def _prevent_workflow_event_delete(*_: object) -> None:
    raise AppendOnlyWorkflowEventError("Workflow events are append-only")
