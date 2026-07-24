from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.human_actions.models import HumanAction
from app.human_actions.repository import HumanActionRepository
from app.human_actions.schemas import (
    HumanActionCreate,
    HumanActionListFilters,
    HumanActionSubmitPayload,
    HumanActionSubmitResponse,
)


class HumanActionPermissionError(BusinessValidationError):
    pass


class HumanActionService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: HumanActionRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or HumanActionRepository(
            session, current_user.company_id
        )
        self.request_repository = request_repository or BusinessRequestRepository(
            session, current_user.company_id
        )

    def _can_view(self, human_action: HumanAction) -> bool:
        if self.current_user.actor_type == ActorType.COMPANY:
            return True
        if human_action.assigned_user_id == self.current_user.user_id:
            return True
        if human_action.assigned_role is not None:
            if (
                self.current_user.actor_type.value == human_action.assigned_role
                or self.current_user.is_manager
            ):
                return True
        # Requesters can view human actions on their own requests
        if human_action.request and human_action.request.requester_user_id == self.current_user.user_id:
            return True
        return False

    async def get(self, action_id: UUID) -> HumanAction:
        human_action = await self.repository.get_by_id(action_id)
        if human_action is None or not self._can_view(human_action):
            raise NotFoundError("Human action not found")
        return human_action

    async def list(self, filters: HumanActionListFilters) -> list[HumanAction]:
        assigned_user_id: UUID | None = None
        assigned_role: str | None = None

        if self.current_user.actor_type == ActorType.COMPANY:
            pass  # Company can see all
        elif self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            assigned_role = ActorType.DEPARTMENT_MANAGER.value
            assigned_user_id = self.current_user.user_id
        else:
            # Employees/external: see actions assigned to them
            assigned_user_id = self.current_user.user_id

        return await self.repository.list(
            status=filters.status,
            request_id=filters.request_id,
            assigned_user_id=assigned_user_id,
            assigned_role=assigned_role,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def create(self, payload: HumanActionCreate) -> HumanAction:
        business_request = await self.request_repository.get_by_id(payload.request_id)
        if business_request is None or not can_view_business_request(
            self.current_user, business_request
        ):
            raise NotFoundError("Business request not found")
        if self.current_user.actor_type not in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            raise HumanActionPermissionError(
                "Only Company accounts or managers can create human actions"
            )

        try:
            human_action = await self.repository.create(
                request_id=payload.request_id,
                action_type=payload.action_type,
                title=payload.title,
                description=payload.description,
                assigned_user_id=payload.assigned_user_id,
                assigned_role=payload.assigned_role,
                decision_package=payload.decision_package,
                due_date=payload.due_date,
            )
            await self.session.commit()
            await self.session.refresh(human_action)
            return human_action
        except Exception:
            await self.session.rollback()
            raise

    async def submit(
        self,
        action_id: UUID,
        payload: HumanActionSubmitPayload,
    ) -> HumanActionSubmitResponse:
        human_action = await self.get(action_id)
        if human_action.status != "pending":
            raise BusinessValidationError(
                "Human action is not in a pending state"
            )
        if self.current_user.actor_type not in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        } and human_action.assigned_user_id != self.current_user.user_id:
            raise HumanActionPermissionError(
                "You are not authorized to submit this action"
            )

        try:
            updated = await self.repository.submit_response(
                action_id,
                decision=payload.decision,
                response=payload.response,
                responding_user_id=self.current_user.user_id,
            )
            if updated is None:
                raise NotFoundError("Human action not found or already resolved")
            await self.session.commit()
            await self.session.refresh(updated)
            return HumanActionSubmitResponse(
                id=updated.id,
                status=updated.status,
                resolved_at=updated.resolved_at,
            )
        except Exception:
            await self.session.rollback()
            raise
