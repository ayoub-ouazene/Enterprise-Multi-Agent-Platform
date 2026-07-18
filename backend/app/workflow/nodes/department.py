from typing import Any

from app.requests.enums import RequestStatus
from app.workflow.state import (
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    WorkflowState,
    add_completed_step,
)


def department_stage_start_node(state: WorkflowState) -> dict[str, Any]:
    if DEPARTMENT_STARTED_STEP in state.planning.completed_steps:
        return {}
    request = state.request.model_copy(
        update={
            "status": RequestStatus.PROCESSING,
            "current_stage": "placeholder_department_processing",
        }
    )
    planning = add_completed_step(state, DEPARTMENT_STARTED_STEP).model_copy(
        update={"current_step": "placeholder_department"}
    )
    execution = state.execution.model_copy(
        update={
            "last_operation": "placeholder_department_processing",
            "last_operation_status": "started",
        }
    )
    return {"request": request, "planning": planning, "execution": execution}


def placeholder_department_node(state: WorkflowState) -> dict[str, Any]:
    """Demonstrate a safe state update without business logic or tools."""

    if DEPARTMENT_COMPLETED_STEP in state.planning.completed_steps:
        return {}
    request = state.request.model_copy(
        update={"current_stage": "placeholder_department_completed"}
    )
    planning = add_completed_step(state, DEPARTMENT_COMPLETED_STEP).model_copy(
        update={"current_step": "completion"}
    )
    execution = state.execution.model_copy(
        update={
            "last_operation": "placeholder_department_processing",
            "last_operation_status": "completed",
        }
    )
    return {"request": request, "planning": planning, "execution": execution}
