from typing import Literal

from langgraph.graph import END

from app.departments.contracts import DepartmentExecutionResult, DepartmentNextAction
from app.workflow.router_output import RouterMessageCategory

from app.workflow.state import (
    COMPLETED_STEP,
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    LEGACY_DEPARTMENT_COMPLETED_STEP,
    LEGACY_DEPARTMENT_STARTED_STEP,
    ROUTED_STEP,
    LEGACY_ROUTED_STEP,
    WorkflowState,
)


NextSkeletonNode = Literal[
    "router",
    "department_stage_start",
    "department_execution",
    "completion",
]


def route_next_skeleton_node(state: WorkflowState) -> NextSkeletonNode:
    completed = frozenset(state.planning.completed_steps)
    if ROUTED_STEP not in completed and LEGACY_ROUTED_STEP not in completed:
        return "router"
    if (
        DEPARTMENT_STARTED_STEP not in completed
        and LEGACY_DEPARTMENT_STARTED_STEP not in completed
    ):
        return "department_stage_start"
    if (
        DEPARTMENT_COMPLETED_STEP not in completed
        and LEGACY_DEPARTMENT_COMPLETED_STEP not in completed
    ):
        return "department_execution"
    if COMPLETED_STEP not in completed:
        return "completion"
    return "completion"


def route_after_router(
    state: WorkflowState,
) -> Literal["department_stage_start", "completion", "__end__"]:
    if state.routing.routing_pending:
        return END
    if (
        state.routing.message_category == RouterMessageCategory.UNSUPPORTED
        and state.routing.is_capability_gap
    ):
        return END
    if state.routing.message_category in {
        RouterMessageCategory.PLATFORM_QUESTION,
        RouterMessageCategory.UNSUPPORTED,
    }:
        return "completion"
    return "department_stage_start"


def route_after_department(
    state: WorkflowState,
) -> Literal[
    "department_execution",
    "tool",
    "collaboration",
    "reviewer",
    "human_action",
    "completion",
    "failure",
]:
    result = DepartmentExecutionResult.model_validate(
        state.execution.department_result
    )
    routes = {
        DepartmentNextAction.CONTINUE_DEPARTMENT: "department_execution",
        DepartmentNextAction.EXECUTE_TOOL: "tool",
        DepartmentNextAction.COLLABORATE: "collaboration",
        DepartmentNextAction.REQUEST_REVIEW: "reviewer",
        DepartmentNextAction.REQUEST_HUMAN_ACTION: "human_action",
        DepartmentNextAction.COMPLETE_REQUEST: "completion",
        DepartmentNextAction.FAIL_REQUEST: "failure",
    }
    return routes[result.next_action]
