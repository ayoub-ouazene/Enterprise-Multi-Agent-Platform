from typing import Any
from uuid import UUID

from datetime import datetime

from sqlalchemy import exists, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.requests.enums import RequestPriority, RequestStatus
from app.requests.models import BusinessRequest


class BusinessRequestRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, request_id: UUID) -> BusinessRequest | None:
        return await self.session.scalar(
            select(BusinessRequest).where(
                BusinessRequest.id == request_id,
                BusinessRequest.company_id == self.company_id,
            )
        )

    async def get_by_id_for_update(
        self,
        request_id: UUID,
    ) -> BusinessRequest | None:
        return await self.session.scalar(
            select(BusinessRequest)
            .where(
                BusinessRequest.id == request_id,
                BusinessRequest.company_id == self.company_id,
            )
            .with_for_update()
        )

    async def list(
        self,
        *,
        status: RequestStatus | None = None,
        priority: RequestPriority | None = None,
        request_type: str | None = None,
        search: str | None = None,
        owner_department_id: UUID | None = None,
        requester_filter_id: UUID | None = None,
        attention_required: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        requester_user_id: UUID | None = None,
        department_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BusinessRequest]:
        statement = select(BusinessRequest).where(
            BusinessRequest.company_id == self.company_id
        )
        if status is not None:
            statement = statement.where(BusinessRequest.status == status)
        if priority is not None:
            statement = statement.where(BusinessRequest.priority == priority)
        if request_type is not None:
            statement = statement.where(BusinessRequest.request_type == request_type)
        if search is not None:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    BusinessRequest.title.ilike(pattern),
                    BusinessRequest.summary.ilike(pattern),
                    BusinessRequest.request_type.ilike(pattern),
                )
            )
        if owner_department_id is not None:
            statement = statement.where(
                BusinessRequest.owner_department_id == owner_department_id
            )
        if requester_filter_id is not None:
            statement = statement.where(
                BusinessRequest.requester_user_id == requester_filter_id
            )
        if created_from is not None:
            statement = statement.where(BusinessRequest.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(BusinessRequest.created_at <= created_to)
        if attention_required is True:
            from app.human_actions.models import HumanAction

            pending_action = exists(
                select(HumanAction.id).where(
                    HumanAction.company_id == self.company_id,
                    HumanAction.request_id == BusinessRequest.id,
                    HumanAction.status == "pending",
                )
            )
            statement = statement.where(
                or_(
                    pending_action,
                    BusinessRequest.status.in_(
                        (
                            RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
                            RequestStatus.WAITING_FOR_HUMAN_ACTION,
                            RequestStatus.FAILED,
                            RequestStatus.REJECTED,
                        )
                    ),
                )
            )

        if requester_user_id is not None and department_id is not None:
            statement = statement.where(
                or_(
                    BusinessRequest.requester_user_id == requester_user_id,
                    BusinessRequest.owner_department_id == department_id,
                    BusinessRequest.active_department_id == department_id,
                )
            )
        elif requester_user_id is not None:
            statement = statement.where(
                BusinessRequest.requester_user_id == requester_user_id
            )
        elif department_id is not None:
            statement = statement.where(
                or_(
                    BusinessRequest.owner_department_id == department_id,
                    BusinessRequest.active_department_id == department_id,
                )
            )

        result = await self.session.scalars(
            statement.order_by(BusinessRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def create(
        self,
        *,
        requester_user_id: UUID,
        requester_employee_id: UUID | None,
        request_type: str,
        title: str,
        summary: str,
        priority: RequestPriority,
        workflow_state: dict[str, Any],
        custom_data: dict[str, Any],
        request_id: UUID | None = None,
    ) -> BusinessRequest:
        business_request = BusinessRequest(
            **({"id": request_id} if request_id is not None else {}),
            company_id=self.company_id,
            requester_user_id=requester_user_id,
            requester_employee_id=requester_employee_id,
            owner_department_id=None,
            active_department_id=None,
            request_type=request_type,
            title=title,
            summary=summary,
            status=RequestStatus.CREATED,
            current_stage="request_received",
            priority=priority,
            workflow_state=workflow_state,
            custom_data=custom_data,
        )
        self.session.add(business_request)
        await self.session.flush()
        return business_request

    async def update(
        self,
        request_id: UUID,
        values: dict[str, object],
    ) -> BusinessRequest | None:
        if not values:
            return await self.get_by_id(request_id)
        return await self.session.scalar(
            update(BusinessRequest)
            .where(
                BusinessRequest.id == request_id,
                BusinessRequest.company_id == self.company_id,
            )
            .values(**values)
            .returning(BusinessRequest)
        )
