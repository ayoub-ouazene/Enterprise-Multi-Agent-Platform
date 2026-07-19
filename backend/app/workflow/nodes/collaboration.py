from typing import Any
from langgraph.runtime import Runtime

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.requests.enums import RequestStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowRuntimeContext, WorkflowState


def customer_support_collaboration_node(state: WorkflowState) -> dict[str, Any]:
    """Compatibility helper that validates and prepares the Step 13 handoff."""
    request = DepartmentCollaborationRequest.model_validate(state.collaboration.request)
    if request.request_id != state.request.request_id or request.sender_department != DepartmentType.CUSTOMER_SUPPORT or request.receiver_department != DepartmentType.IT or request.action != "diagnose_external_technical_issue":
        raise InactiveWorkflowNodeError("Only Customer Support diagnostic IT collaboration is allowed")
    return {"request": state.request.model_copy(update={
        "status": RequestStatus.WAITING_FOR_DEPARTMENT,
        "current_stage": "customer_support_waiting_for_it"}),
        "collaboration": state.collaboration.model_copy(update={"is_active": True})}


async def department_collaboration_node(state: WorkflowState,
    runtime: Runtime[WorkflowRuntimeContext]) -> dict[str, Any]:
    request = DepartmentCollaborationRequest.model_validate(state.collaboration.request)
    if request.request_id != state.request.request_id:
        raise InactiveWorkflowNodeError("Collaboration Request ID is invalid")
    if request.sender_department == DepartmentType.CUSTOMER_SUPPORT and request.receiver_department == DepartmentType.IT and request.action == "diagnose_external_technical_issue":
        service = runtime.context.department_execution_service
        if service is None:
            raise InactiveWorkflowNodeError("IT collaboration is unavailable")
        result = await service.execute_it_collaboration(state, request)
        collaboration = state.collaboration.model_copy(update={
            "structured_result": result.model_dump(mode="json"), "is_active": False})
        request_state = state.request.model_copy(update={"status": RequestStatus.PROCESSING,
            "current_stage": "customer_support_received_it_diagnosis"})
        execution = state.execution.model_copy(update={"department_result": {}})
        return {"request": request_state, "collaboration": collaboration, "execution": execution}
    finance_allowed = {
        (DepartmentType.IT, DepartmentType.FINANCE, "validate_it_purchase_budget"),
        (DepartmentType.PROCUREMENT, DepartmentType.FINANCE, "validate_procurement_purchase"),
    }
    if (request.sender_department, request.receiver_department, request.action) in finance_allowed:
        service = (
            runtime.context.department_execution_service
            if runtime.context is not None else None
        )
        if service is None:
            request_state = state.request.model_copy(update={
                "status": RequestStatus.WAITING_FOR_DEPARTMENT,
                "current_stage": f"{request.sender_department.value}_waiting_for_finance",
            })
            return {
                "request": request_state,
                "collaboration": state.collaboration.model_copy(update={"is_active": True}),
            }
        result = await service.execute_finance_collaboration(state, request)
        collaboration = state.collaboration.model_copy(update={
            "structured_result": result.model_dump(mode="json"), "is_active": False})
        request_state = state.request.model_copy(update={
            "status": RequestStatus.PROCESSING,
            "current_stage": f"{request.sender_department.value}_received_finance_validation",
        })
        execution = state.execution.model_copy(update={"department_result": {}})
        return {"request": request_state, "collaboration": collaboration, "execution": execution}
    allowed = {(DepartmentType.IT, DepartmentType.PROCUREMENT, "find_it_asset_suppliers")}
    if (request.sender_department, request.receiver_department, request.action) not in allowed:
        raise InactiveWorkflowNodeError("The collaboration operation is not active")
    request_state = state.request.model_copy(update={"status": RequestStatus.WAITING_FOR_DEPARTMENT,
        "current_stage": f"it_waiting_for_{request.receiver_department.value}"})
    return {"request": request_state,
        "collaboration": state.collaboration.model_copy(update={"is_active": True})}
