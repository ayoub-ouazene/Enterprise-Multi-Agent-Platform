from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.requests.models import BusinessRequest
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.models import WorkflowEvent


class WorkflowEventRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def append(
        self,
        *,
        request_id: UUID,
        event_type: WorkflowEventType,
        stage: str | None,
        title: str,
        message: str,
        actor_type: WorkflowEventActorType,
        actor_user_id: UUID | None,
        department_id: UUID | None,
        visibility: WorkflowEventVisibility,
        event_data: dict[str, object],
    ) -> WorkflowEvent | None:
        locked_request_id = await self.session.scalar(
            select(BusinessRequest.id)
            .where(
                BusinessRequest.id == request_id,
                BusinessRequest.company_id == self.company_id,
            )
            .with_for_update()
        )
        if locked_request_id is None:
            return None

        current_sequence = await self.session.scalar(
            select(func.coalesce(func.max(WorkflowEvent.sequence_number), 0)).where(
                WorkflowEvent.company_id == self.company_id,
                WorkflowEvent.request_id == request_id,
            )
        )
        event = WorkflowEvent(
            company_id=self.company_id,
            request_id=request_id,
            event_type=event_type,
            stage=stage,
            title=title,
            message=message,
            actor_type=actor_type,
            actor_user_id=actor_user_id,
            department_id=department_id,
            visibility=visibility,
            event_data=event_data,
            sequence_number=int(current_sequence or 0) + 1,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_for_request(
        self,
        request_id: UUID,
        *,
        visibilities: frozenset[WorkflowEventVisibility],
        event_type: WorkflowEventType | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEvent]:
        statement = select(WorkflowEvent).where(
            WorkflowEvent.company_id == self.company_id,
            WorkflowEvent.request_id == request_id,
            WorkflowEvent.visibility.in_(visibilities),
        )
        if event_type is not None:
            statement = statement.where(WorkflowEvent.event_type == event_type)
        result = await self.session.scalars(
            statement.order_by(WorkflowEvent.sequence_number.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())
