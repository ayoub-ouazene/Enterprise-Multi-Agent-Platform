from typing import Any

from langgraph.runtime import Runtime

from app.departments.contracts import DepartmentExecutionResult, DepartmentNextAction
from app.departments.exceptions import DepartmentExecutionError
from app.requests.enums import RequestStatus
from app.workflow.state import (
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    LEGACY_DEPARTMENT_COMPLETED_STEP,
    LEGACY_DEPARTMENT_STARTED_STEP,
    WorkflowRuntimeContext,
    WorkflowState,
    add_completed_step,
    apply_state_update,
)


def department_stage_start_node(state: WorkflowState) -> dict[str, Any]:
    completed = frozenset(state.planning.completed_steps)
    if (
        DEPARTMENT_STARTED_STEP in completed
        or LEGACY_DEPARTMENT_STARTED_STEP in completed
    ):
        return {}
    request = state.request.model_copy(
        update={
            "status": RequestStatus.PROCESSING,
            "current_stage": "department_execution_started",
        }
    )
    planning = add_completed_step(state, DEPARTMENT_STARTED_STEP).model_copy(
        update={"current_step": "department_execution"}
    )
    execution = state.execution.model_copy(
        update={
            "last_operation": "department_execution",
            "last_operation_status": "started",
        }
    )
    return {"request": request, "planning": planning, "execution": execution}


async def department_execution_node(
    state: WorkflowState,
    runtime: Runtime[WorkflowRuntimeContext],
) -> dict[str, Any]:
    """Execute only the implementation resolved from trusted persisted state."""

    completed = frozenset(state.planning.completed_steps)
    if (
        DEPARTMENT_COMPLETED_STEP in completed
        or LEGACY_DEPARTMENT_COMPLETED_STEP in completed
    ):
        return {}
    service = runtime.context.department_execution_service
    if service is None:
        raise DepartmentExecutionError("Department execution service is unavailable")
    update = runtime.context.precomputed_department_result
    if update is not None and "department_type" in update:
        update = service._safe_state_update(
            state, DepartmentExecutionResult.model_validate(update)
        )
    elif update is None:
        update = await service.execute(state)
    updated_state = apply_state_update(state, update)
    result = DepartmentExecutionResult.model_validate(
        updated_state.execution.department_result
    )
    planning = updated_state.planning.model_copy(
        update={"current_step": result.next_action.value}
    )
    if result.next_action in {
        DepartmentNextAction.COMPLETE_REQUEST,
        DepartmentNextAction.FAIL_REQUEST,
    }:
        planning = add_completed_step(updated_state, DEPARTMENT_COMPLETED_STEP).model_copy(
            update={"current_step": result.next_action.value}
        )
    elif result.next_action == DepartmentNextAction.WAIT_FOR_USER_INPUT:
        planning = planning.model_copy(update={"current_step": result.next_action.value})
    update["planning"] = planning
    return update
