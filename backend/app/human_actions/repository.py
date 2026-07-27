from uuid import UUID

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.requests.models import BusinessRequest
from sqlalchemy.ext.asyncio import AsyncSession

from app.human_actions.models import HumanAction


class HumanActionRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, action_id: UUID) -> HumanAction | None:
        return await self.session.scalar(
            select(HumanAction).options(selectinload(HumanAction.request)).where(
                HumanAction.id == action_id,
                HumanAction.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        status: str | None = None,
        request_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
        assigned_role: str | None = None,
        action_type: str | None = None,
        department_id: UUID | None = None,
        due_before=None,
        due_after=None,
        overdue_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[HumanAction]:
        statement = select(HumanAction).options(selectinload(HumanAction.request)).where(
            HumanAction.company_id == self.company_id
        )
        if department_id is not None:
            statement = statement.join(
                BusinessRequest, BusinessRequest.id == HumanAction.request_id
            ).where(
                (BusinessRequest.owner_department_id == department_id)
                | (BusinessRequest.active_department_id == department_id)
            )
        if status is not None:
            statement = statement.where(HumanAction.status == status)
        if request_id is not None:
            statement = statement.where(HumanAction.request_id == request_id)
        if assigned_user_id is not None:
            statement = statement.where(
                HumanAction.assigned_user_id == assigned_user_id
            )
        if assigned_role is not None:
            statement = statement.where(
                HumanAction.assigned_role == assigned_role
            )
        if action_type is not None:
            statement = statement.where(HumanAction.action_type == action_type)
        if due_before is not None:
            statement = statement.where(HumanAction.due_date <= due_before)
        if due_after is not None:
            statement = statement.where(HumanAction.due_date >= due_after)
        if overdue_only:
            statement = statement.where(
                HumanAction.status == "pending",
                HumanAction.due_date < datetime.now(UTC),
            )
        result = await self.session.scalars(
            statement.order_by(HumanAction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def create(
        self,
        *,
        request_id: UUID,
        action_type: str,
        title: str,
        description: str,
        assigned_user_id: UUID | None = None,
        assigned_role: str | None = None,
        decision_package: dict,
        due_date=None,
    ) -> HumanAction:
        human_action = HumanAction(
            company_id=self.company_id,
            request_id=request_id,
            action_type=action_type,
            title=title,
            description=description,
            assigned_user_id=assigned_user_id,
            assigned_role=assigned_role,
            decision_package=decision_package,
            due_date=due_date,
        )
        self.session.add(human_action)
        await self.session.flush()
        return human_action

    async def submit_response(
        self,
        action_id: UUID,
        *,
        decision: str,
        response: str,
        responding_user_id: UUID,
        expected_updated_at=None,
    ) -> HumanAction | None:
        from datetime import UTC, datetime

        return await self.session.scalar(
            update(HumanAction)
            .where(
                HumanAction.id == action_id,
                HumanAction.company_id == self.company_id,
                HumanAction.status == "pending",
                *(
                    [HumanAction.updated_at == expected_updated_at]
                    if expected_updated_at is not None
                    else []
                ),
            )
            .values(
                status="resolved",
                response={
                    "decision": decision,
                    "response": response,
                    "responding_user_id": str(responding_user_id),
                    "responded_at": datetime.now(UTC).isoformat(),
                },
                resolved_at=datetime.now(UTC),
            )
            .returning(HumanAction)
        )
