from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.requests.enums import RequestStatus
from app.requests.models import BusinessRequest
from app.requests.repository import BusinessRequestRepository
from app.workflow.exceptions import (
    InvalidWorkflowStateError,
    UnsupportedWorkflowStateVersionError,
    WorkflowPersistenceError,
)
from app.workflow.state import (
    STATE_VERSION,
    WorkflowState,
    build_initial_workflow_state,
)


class WorkflowPersistence:
    """Tenant-scoped JSONB workflow-state persistence without transaction ownership."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        repository: BusinessRequestRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.repository = repository or BusinessRequestRepository(
            session,
            current_user.company_id,
        )

    async def load_request(
        self,
        request_id: UUID,
        *,
        for_update: bool = False,
    ) -> BusinessRequest | None:
        if for_update:
            return await self.repository.get_by_id_for_update(request_id)
        return await self.repository.get_by_id(request_id)

    def load_state(self, business_request: BusinessRequest) -> WorkflowState:
        raw_state = business_request.workflow_state
        if not raw_state:
            if business_request.status == RequestStatus.CREATED:
                return build_initial_workflow_state(business_request)
            raise InvalidWorkflowStateError(
                "A started request has no persisted workflow state"
            )
        if not isinstance(raw_state, dict):
            raise InvalidWorkflowStateError("Stored workflow state is not an object")

        version = raw_state.get("state_version")
        if version != STATE_VERSION:
            if version is not None:
                raise UnsupportedWorkflowStateVersionError(
                    "Stored workflow-state version is unsupported"
                )
            raise InvalidWorkflowStateError("Stored workflow state has no version")

        try:
            state = WorkflowState.model_validate(raw_state)
        except ValidationError as exc:
            raise InvalidWorkflowStateError("Stored workflow state is invalid") from exc

        self._validate_identity(state, business_request)
        return state

    def _validate_identity(
        self,
        state: WorkflowState,
        business_request: BusinessRequest,
    ) -> None:
        request_state = state.request
        if (
            request_state.request_id != business_request.id
            or request_state.company_id != business_request.company_id
            or request_state.company_id != self.current_user.company_id
            or request_state.requester_user_id != business_request.requester_user_id
        ):
            raise InvalidWorkflowStateError(
                "Stored workflow state does not match its Business Request"
            )
        database_fields: tuple[tuple[Any, Any], ...] = (
            (request_state.status, business_request.status),
            (request_state.current_stage, business_request.current_stage),
            (request_state.owner_department_id, business_request.owner_department_id),
            (request_state.active_department_id, business_request.active_department_id),
        )
        if any(
            state_value != database_value
            for state_value, database_value in database_fields
        ):
            raise InvalidWorkflowStateError(
                "Stored workflow state conflicts with Business Request state"
            )

    async def save_checkpoint(
        self,
        state: WorkflowState,
    ) -> BusinessRequest:
        if state.request.company_id != self.current_user.company_id:
            raise InvalidWorkflowStateError("Workflow tenant context is invalid")

        values: dict[str, object] = {
            "workflow_state": state.to_storage(),
            "status": state.request.status,
            "current_stage": state.request.current_stage,
            "owner_department_id": state.request.owner_department_id,
            "active_department_id": state.request.active_department_id,
            "request_type": state.request.request_type,
            "summary": state.request.summary,
            "final_decision": state.result.decision,
            "final_reason": state.result.reason,
        }
        if state.request.status == RequestStatus.COMPLETED:
            if state.result.completed_at is None:
                raise InvalidWorkflowStateError(
                    "Completed workflow state requires a completion timestamp"
                )
            values["completed_at"] = state.result.completed_at

        try:
            updated = await self.repository.update(state.request.request_id, values)
        except Exception as exc:
            raise WorkflowPersistenceError(
                "Workflow checkpoint persistence failed"
            ) from exc
        if updated is None:
            raise WorkflowPersistenceError(
                "Business request disappeared during workflow"
            )
        return updated
