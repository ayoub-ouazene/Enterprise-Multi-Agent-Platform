from typing import Any

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.requests.enums import RequestStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def customer_support_collaboration_node(state: WorkflowState) -> dict[str, Any]:
    request = DepartmentCollaborationRequest.model_validate(state.collaboration.request)
    if (
        request.request_id != state.request.request_id
        or request.sender_department != DepartmentType.CUSTOMER_SUPPORT
        or request.receiver_department != DepartmentType.IT
        or request.action != "diagnose_external_technical_issue"
    ):
        raise InactiveWorkflowNodeError("Only Customer Support diagnostic IT preparation is active")
    request_state = state.request.model_copy(update={
        "status": RequestStatus.WAITING_FOR_DEPARTMENT,
        "current_stage": "customer_support_waiting_for_it",
    })
    collaboration = state.collaboration.model_copy(update={"is_active": True})
    return {"request": request_state, "collaboration": collaboration}
