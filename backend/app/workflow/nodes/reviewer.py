"""Active reviewer node for the centralized one-revision quality-control loop."""

from typing import Any

from langgraph.runtime import Runtime

from app.departments.contracts import DepartmentExecutionResult
from app.requests.enums import RequestStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.review.service import ReviewService
from app.workflow.state import (
    DEPARTMENT_COMPLETED_STEP,
    REVIEW_COMPLETED_STEP,
    WorkflowRuntimeContext,
    WorkflowState,
    apply_state_update,
)


async def reviewer_node(
    state: WorkflowState,
    runtime: Runtime[WorkflowRuntimeContext],
) -> dict[str, Any]:
    """Execute centralized review, apply decision, and produce state update."""
    if not state.execution.department_result:
        raise InactiveWorkflowNodeError("Reviewer called without a department result")

    service: ReviewService | None = runtime.context.review_service
    if service is None:
        if runtime.context.departments is None:
            raise InactiveWorkflowNodeError("Workflow runtime context is missing")
        from app.core.config import get_settings
        service = ReviewService(get_settings())

    # Run reviewer
    reviewer_result = await service.execute_review(state)

    # Apply decision to state
    update = service.apply_decision(state, reviewer_result)
    updated_state = apply_state_update(state, update)

    # On revision, clear department completion so the dept re-runs with feedback.
    if reviewer_result.decision.value == "revision_required":
        planning = updated_state.planning.model_copy(
            update={
                "completed_steps": [
                    s for s in updated_state.planning.completed_steps
                    if s != DEPARTMENT_COMPLETED_STEP
                ],
                "current_step": "reviewer_requested_revision",
            }
        )
        update["planning"] = planning
        updated_state = apply_state_update(updated_state, {"planning": planning})
    else:
        # Mark reviewer completed so routing does not loop back
        planning = updated_state.planning.model_copy(
            update={
                "completed_steps": updated_state.planning.completed_steps + [REVIEW_COMPLETED_STEP],
            }
        )
        update["planning"] = planning
        updated_state = apply_state_update(updated_state, {"planning": planning})

    # On human escalation, enrich human action package and stage the request
    if reviewer_result.decision.value == "human_escalation_required":
        result = DepartmentExecutionResult.model_validate(state.execution.department_result)
        enriched = service.prepare_human_action_from_review(updated_state, result)
        request = updated_state.request.model_copy(
            update={
                "status": RequestStatus.WAITING_FOR_HUMAN_ACTION,
                "current_stage": "reviewer_human_escalation",
            }
        )
        human = updated_state.human_action.model_copy(
            update={
                "required": True,
                "request": enriched.model_dump(mode="json"),
                "status": "pending",
            }
        )
        update["request"] = request
        update["human_action"] = human
        return {
            "request": request,
            "planning": update["planning"],
            "review": update["review"],
            "human_action": human,
        }

    # Ensure request stage reflects awaiting review (it may already)
    if updated_state.request.status != RequestStatus.PROCESSING:
        request = updated_state.request.model_copy(
            update={"status": RequestStatus.PROCESSING}
        )
        update["request"] = request

    return {
        key: update[key]
        for key in ("request", "planning", "review", "human_action")
        if key in update
    }
