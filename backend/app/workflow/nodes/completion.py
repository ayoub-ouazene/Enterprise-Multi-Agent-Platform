from datetime import UTC, datetime
from typing import Any

from app.requests.enums import RequestStatus
from app.workflow.state import (
    COMPLETED_STEP,
    WorkflowState,
    add_completed_step,
)
from app.workflow.router_output import RouterMessageCategory
from app.departments.contracts import DepartmentExecutionResult


def completion_node(state: WorkflowState) -> dict[str, Any]:
    if COMPLETED_STEP in state.planning.completed_steps:
        return {}
    completed_at = datetime.now(UTC)
    request = state.request.model_copy(
        update={
            "status": RequestStatus.COMPLETED,
            "current_stage": RequestStatus.COMPLETED.value,
        }
    )
    planning = add_completed_step(state, COMPLETED_STEP).model_copy(
        update={"current_step": None, "pending_steps": []}
    )
    final_response = "The request completed its placeholder department workflow."
    reason = "The routed placeholder workflow completed successfully."
    decision = "completed"
    if state.execution.department_result:
        department_result = DepartmentExecutionResult.model_validate(
            state.execution.department_result
        )
        final_response = department_result.user_message
        reason = department_result.reason
        decision = department_result.decision
    if state.routing.message_category == RouterMessageCategory.PLATFORM_QUESTION:
        final_response = state.routing.platform_answer or "Platform guidance is unavailable."
        reason = state.routing.routing_reason or "Platform question answered."
        decision = "answered"
    elif state.routing.message_category == RouterMessageCategory.UNSUPPORTED:
        final_response = (
            state.routing.unsupported_reason
            or "This request is not supported by the platform."
        )
        reason = state.routing.routing_reason or "The request is unsupported."
        decision = "unsupported"

    result = state.result.model_copy(
        update={
            "decision": decision,
            "reason": reason,
            "final_response": final_response,
            "completed_at": completed_at,
        }
    )
    return {"request": request, "planning": planning, "result": result}
