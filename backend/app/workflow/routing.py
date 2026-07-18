from typing import Literal

from langgraph.graph import END

from app.workflow.router_output import RouterMessageCategory

from app.workflow.state import (
    COMPLETED_STEP,
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    ROUTED_STEP,
    LEGACY_ROUTED_STEP,
    WorkflowState,
)


NextSkeletonNode = Literal[
    "router",
    "department_stage_start",
    "placeholder_department",
    "completion",
]


def route_next_skeleton_node(state: WorkflowState) -> NextSkeletonNode:
    completed = frozenset(state.planning.completed_steps)
    if ROUTED_STEP not in completed and LEGACY_ROUTED_STEP not in completed:
        return "router"
    if DEPARTMENT_STARTED_STEP not in completed:
        return "department_stage_start"
    if DEPARTMENT_COMPLETED_STEP not in completed:
        return "placeholder_department"
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
