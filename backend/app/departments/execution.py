from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import DepartmentType
from app.core.exceptions import NotFoundError
from app.departments.contracts import (
    DepartmentCollaborationRequest,
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    HumanResponseContext,
    ReviewFeedbackContext,
)
from app.departments.exceptions import (
    DepartmentContextMismatchError,
    DepartmentResultValidationError,
    DepartmentStateUpdateError,
)
from app.departments.registry import DepartmentRegistry, build_default_department_registry
from app.departments.repository import DepartmentRepository
from app.requests.repository import BusinessRequestRepository
from app.workflow.state import WorkflowState, add_completed_step, apply_state_update


class DepartmentExecutionService:
    """Resolve and execute one trusted tenant department without committing."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        *,
        request_repository: BusinessRequestRepository | None = None,
        department_repository: DepartmentRepository | None = None,
        registry: DepartmentRegistry | None = None,
    ) -> None:
        self.current_user = current_user
        self.request_repository = request_repository or BusinessRequestRepository(
            session,
            current_user.company_id,
        )
        self.department_repository = department_repository or DepartmentRepository(
            session,
            current_user.company_id,
        )
        self.registry = registry or build_default_department_registry()

    async def execute(self, state: WorkflowState) -> dict[str, Any]:
        business_request = await self.request_repository.get_by_id_for_update(
            state.request.request_id
        )
        if business_request is None:
            raise NotFoundError("Business request not found")
        if (
            business_request.company_id != self.current_user.company_id
            or business_request.company_id != state.request.company_id
            or business_request.requester_user_id != state.request.requester_user_id
        ):
            raise NotFoundError("Business request not found")

        owner_id = business_request.owner_department_id
        active_id = business_request.active_department_id
        if owner_id is None or active_id is None:
            raise DepartmentContextMismatchError(
                "Department execution requires owner and active departments"
            )
        if (
            state.request.owner_department_id != owner_id
            or state.request.active_department_id != active_id
        ):
            raise DepartmentContextMismatchError(
                "Workflow department identity conflicts with the persisted request"
            )

        owner = await self.department_repository.get_by_id(owner_id)
        active = await self.department_repository.get_by_id(active_id)
        if owner is None or active is None:
            raise NotFoundError("Department not found")
        if (
            owner.company_id != self.current_user.company_id
            or active.company_id != self.current_user.company_id
        ):
            raise NotFoundError("Department not found")
        if not owner.is_active or not active.is_active:
            raise DepartmentContextMismatchError("The active department is unavailable")
        if owner.id != active.id or owner.department_type != active.department_type:
            raise DepartmentContextMismatchError(
                "Active and owner departments must match before collaboration is enabled"
            )
        if (
            state.routing.selected_department is not None
            and state.routing.selected_department != owner.department_type
        ):
            raise DepartmentContextMismatchError(
                "The persisted Router result conflicts with the owner department"
            )

        agent = self.registry.resolve(active.department_type)
        context = self._build_context(
            state,
            business_request=business_request,
            owner_department_type=owner.department_type,
            active_department_type=active.department_type,
        )
        raw_result = await agent.execute(context)
        try:
            result = DepartmentExecutionResult.model_validate(raw_result)
        except ValidationError as exc:
            raise DepartmentResultValidationError(
                "The department returned an invalid structured result"
            ) from exc
        if result.department_type != active.department_type:
            raise DepartmentResultValidationError(
                "The department result does not match the active department"
            )
        return self._safe_state_update(state, result)

    @staticmethod
    def _build_context(
        state: WorkflowState,
        *,
        business_request: Any,
        owner_department_type: DepartmentType,
        active_department_type: DepartmentType,
    ) -> DepartmentExecutionContext:
        collaboration_input = None
        if state.collaboration.request:
            collaboration_input = DepartmentCollaborationRequest.model_validate(
                state.collaboration.request
            )
        review_feedback = None
        if state.review.feedback:
            review_feedback = ReviewFeedbackContext.model_validate(
                state.review.feedback
            )
        human_response = None
        if state.human_action.response:
            human_response = HumanResponseContext.model_validate(
                state.human_action.response
            )
        return DepartmentExecutionContext(
            request_id=state.request.request_id,
            company_id=state.request.company_id,
            requester_user_id=state.request.requester_user_id,
            requester_employee_id=state.request.requester_employee_id,
            owner_department_type=owner_department_type,
            active_department_type=active_department_type,
            request_type=state.request.request_type,
            request_summary=state.request.summary,
            current_stage=state.request.current_stage,
            current_plan=state.planning.current_plan,
            completed_steps=state.planning.completed_steps,
            pending_steps=state.planning.pending_steps,
            relevant_custom_data=business_request.custom_data,
            latest_user_input=state.routing.latest_answer,
            collaboration_input=collaboration_input,
            review_feedback=review_feedback,
            human_response=human_response,
        )

    @staticmethod
    def _safe_state_update(
        state: WorkflowState,
        result: DepartmentExecutionResult,
    ) -> dict[str, Any]:
        updates = result.state_updates
        if updates.current_stage is not None and updates.current_stage != result.current_stage:
            raise DepartmentStateUpdateError(
                "Conflicting department current-stage updates are prohibited"
            )

        request = state.request.model_copy(
            update={"current_stage": result.current_stage}
        )
        planning = add_completed_step(state, result.completed_step)
        if updates.planning is not None:
            planning_values = updates.planning.model_dump(exclude_none=True)
            planning = planning.model_copy(update=planning_values)
        if len(planning.completed_steps) != len(set(planning.completed_steps)):
            raise DepartmentStateUpdateError("Completed workflow steps must be unique")
        if set(planning.completed_steps).intersection(planning.pending_steps):
            raise DepartmentStateUpdateError(
                "A completed workflow step cannot remain pending"
            )

        execution = state.execution
        if updates.execution is not None:
            execution = execution.model_copy(
                update=updates.execution.model_dump(exclude_none=True)
            )
        execution = execution.model_copy(
            update={"department_result": result.model_dump(mode="json")}
        )

        collaboration = state.collaboration
        if updates.collaboration is not None:
            collaboration = collaboration.model_copy(
                update={
                    "request": (
                        updates.collaboration.request.model_dump(mode="json")
                        if updates.collaboration.request is not None
                        else {}
                    ),
                    "structured_result": (
                        updates.collaboration.result.model_dump(mode="json")
                        if updates.collaboration.result is not None
                        else {}
                    ),
                    "is_active": updates.collaboration.is_active,
                }
            )

        review = state.review
        if updates.review is not None:
            review_values = updates.review.model_dump(
                mode="json",
                exclude_none=True,
            )
            review = review.model_copy(update=review_values)

        human_action = state.human_action
        if updates.human_action is not None:
            human_values = updates.human_action.model_dump(
                mode="json",
                exclude_none=True,
            )
            human_action = human_action.model_copy(update=human_values)

        result_state = state.result
        if updates.result is not None:
            result_state = result_state.model_copy(
                update=updates.result.model_dump(exclude_none=True)
            )
        if result.next_action.value == "complete_request":
            result_state = result_state.model_copy(
                update={
                    "decision": result.decision,
                    "reason": result.reason,
                    "final_response": result.user_message,
                }
            )

        merged = apply_state_update(
            state,
            {
                "request": request,
                "planning": planning,
                "execution": execution,
                "collaboration": collaboration,
                "review": review,
                "human_action": human_action,
                "result": result_state,
            },
        )
        return {
            "request": merged.request,
            "planning": merged.planning,
            "execution": merged.execution,
            "collaboration": merged.collaboration,
            "review": merged.review,
            "human_action": merged.human_action,
            "result": merged.result,
        }
