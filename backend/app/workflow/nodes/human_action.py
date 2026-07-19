from typing import Any

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionResult
from app.requests.enums import RequestStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def customer_support_human_action_node(state: WorkflowState) -> dict[str, Any]:
    result = DepartmentExecutionResult.model_validate(state.execution.department_result)
    if result.department_type not in {
        DepartmentType.CUSTOMER_SUPPORT, DepartmentType.IT, DepartmentType.FINANCE
    } or result.human_action_request is None:
        raise InactiveWorkflowNodeError("Only prepared department human actions are active")
    stages = {
        DepartmentType.CUSTOMER_SUPPORT: "customer_support_waiting_for_human_support",
        DepartmentType.IT: "it_waiting_for_technician",
        DepartmentType.FINANCE: "finance_waiting_for_approval",
    }
    request_state = state.request.model_copy(update={
        "status": RequestStatus.WAITING_FOR_HUMAN_ACTION,
        "current_stage": stages[result.department_type],
    })
    human = state.human_action.model_copy(update={
        "required": True,
        "request": result.human_action_request.model_dump(mode="json"),
        "status": "pending",
    })
    return {"request": request_state, "human_action": human}
