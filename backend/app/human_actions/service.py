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
    HumanActionResponse,
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

    def _can_respond(self, human_action: HumanAction) -> bool:
        if human_action.status != "pending":
            return False
        if self.current_user.actor_type in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            return True
        return human_action.assigned_user_id == self.current_user.user_id

    @staticmethod
    def _allowed_decisions_for(action_type: str) -> list[str]:
        mapping: dict[str, list[str]] = {
            "supplier_selection": ["selected", "rejected"],
            "technician_action": ["completed", "failed", "unable"],
            "onboarding_confirmation": ["completed", "failed", "unable"],
            "information_request": ["submitted", "unable"],
            "identity_verification": ["verified", "rejected", "unable"],
        }
        return mapping.get(action_type, ["approved", "rejected"])

    def _to_response(self, human_action: HumanAction) -> HumanActionResponse:
        request_title: str | None = None
        request_status: str | None = None
        if human_action.request is not None:
            request_title = human_action.request.title
            request_status = human_action.request.status.value if hasattr(
                human_action.request.status, "value"
            ) else str(human_action.request.status)
        return HumanActionResponse.model_validate(
            human_action,
            from_attributes=True,
        ).model_copy(update={
            "allowed_decisions": self._allowed_decisions_for(human_action.action_type),
            "can_respond": self._can_respond(human_action),
            "request_title": request_title,
            "request_status": request_status,
        })

    async def get(self, action_id: UUID) -> HumanActionResponse:
        human_action = await self.repository.get_by_id(action_id)
        if human_action is None or not self._can_view(human_action):
            raise NotFoundError("Human action not found")
        return self._to_response(human_action)

    async def list_for_user(self, filters: HumanActionListFilters) -> list[HumanActionResponse]:
        items = await self.list(filters)
        return [self._to_response(item) for item in items]

    async def list_raw(self, filters: HumanActionListFilters) -> list[HumanAction]:
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

    async def list(self, filters: HumanActionListFilters) -> list[HumanActionResponse]:
        raw_items = await self.list_raw(filters)
        return [self._to_response(item) for item in raw_items]

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
