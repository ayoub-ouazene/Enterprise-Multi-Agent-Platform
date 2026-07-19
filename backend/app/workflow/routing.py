from typing import Literal

from langgraph.graph import END

from app.departments.contracts import DepartmentExecutionResult, DepartmentNextAction
from app.core.enums import DepartmentType
from app.requests.enums import RequestStatus
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
from app.workflow.collaboration.enums import CollaborationRuntimeStatus


NextSkeletonNode = Literal[
    "router",
    "department_stage_start",
    "department_execution",
    "collaboration_start",
    "collaboration_receiver",
    "collaboration_return",
    "completion",
    "__end__",
]


def route_next_skeleton_node(state: WorkflowState) -> NextSkeletonNode:
    if state.human_action.required and state.request.status == RequestStatus.WAITING_FOR_HUMAN_ACTION:
        return END
    active_collaboration = state.collaboration.active
    if active_collaboration is not None:
        if (
            state.collaboration.request
            and active_collaboration.status == CollaborationRuntimeStatus.RUNNING
        ):
            return "collaboration_start"
        if active_collaboration.status in {
            CollaborationRuntimeStatus.COMPLETED,
            CollaborationRuntimeStatus.FAILED,
        }:
            return "collaboration_return"
        return "collaboration_receiver"
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
    "__end__",
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
        DepartmentNextAction.WAIT_FOR_USER_INPUT: END,
        DepartmentNextAction.COMPLETE_REQUEST: "completion",
        DepartmentNextAction.FAIL_REQUEST: "failure",
    }
    return routes[result.next_action]


def route_after_collaboration(state: WorkflowState) -> Literal["department_execution", "__end__"]:
    result = state.collaboration.structured_result
    if result and result.get("sender_department") in {
        DepartmentType.CUSTOMER_SUPPORT.value,
        DepartmentType.HR.value,
    } and result.get("receiver_department") == DepartmentType.IT.value:
        return "department_execution"
    if result and result.get("sender_department") == DepartmentType.FINANCE.value and result.get("receiver_department") in {
        DepartmentType.IT.value, DepartmentType.PROCUREMENT.value
    }:
        return "department_execution"
    return END


def route_after_collaboration_start(
    state: WorkflowState,
) -> Literal["collaboration_receiver", "collaboration_return"]:
    active = state.collaboration.active
    if active is not None and active.status == CollaborationRuntimeStatus.COMPLETED:
        return "collaboration_return"
    return "collaboration_receiver"


def route_after_collaboration_receiver(
    state: WorkflowState,
) -> Literal["collaboration_start", "collaboration_return", "__end__"]:
    if state.human_action.required and state.request.status == RequestStatus.WAITING_FOR_HUMAN_ACTION:
        return END
    active = state.collaboration.active
    if active is None:
        return END
    if (
        state.collaboration.request
        and active.status == CollaborationRuntimeStatus.RUNNING
    ):
        return "collaboration_start"
    return "collaboration_return"


def route_after_collaboration_return(
    state: WorkflowState,
) -> Literal["collaboration_receiver", "department_execution"]:
    if state.collaboration.active is not None:
        return "collaboration_receiver"
    return "department_execution"
