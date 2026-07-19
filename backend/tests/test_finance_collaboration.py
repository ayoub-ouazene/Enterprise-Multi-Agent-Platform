import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.requests.enums import RequestStatus
from app.workflow.nodes.collaboration import department_collaboration_node
from app.workflow.state import build_initial_workflow_state


def state_and_request(sender: DepartmentType, action: str):
    request_id, company_id, owner_id = uuid4(), uuid4(), uuid4()
    business_request = SimpleNamespace(
        id=request_id, company_id=company_id, requester_user_id=uuid4(),
        requester_employee_id=None, owner_department_id=owner_id,
        active_department_id=owner_id, request_type="purchase_validation",
        status=RequestStatus.PROCESSING, current_stage="department_processing",
        summary="Validate purchase", workflow_state={}, custom_data={},
    )
    state = build_initial_workflow_state(business_request)
    collaboration = DepartmentCollaborationRequest(
        request_id=request_id, sender_department=sender,
        receiver_department=DepartmentType.FINANCE, action=action,
        payload={"estimated_cost": "100.00", "currency": "USD"},
        expected_output={"decision": "validated_or_rejected"},
    )
    state.collaboration.request = collaboration.model_dump(mode="json")
    return state, collaboration


def test_it_finance_collaboration_preserves_request_and_owner() -> None:
    state, collaboration = state_and_request(
        DepartmentType.IT, "validate_it_purchase_budget"
    )
    service = AsyncMock()
    service.execute_finance_collaboration.return_value = SimpleNamespace(
        model_dump=lambda **_: {
            "request_id": str(collaboration.request_id), "sender_department": "finance",
            "receiver_department": "it", "action": collaboration.action,
            "status": "completed", "result": {"budget_validated": True},
            "reason": "Budget validated",
        }
    )
    runtime = SimpleNamespace(context=SimpleNamespace(department_execution_service=service))
    update = asyncio.run(department_collaboration_node(state, runtime))
    assert update["request"].request_id == state.request.request_id
    assert update["request"].owner_department_id == state.request.owner_department_id
    assert update["collaboration"].structured_result["receiver_department"] == "it"


def test_future_procurement_collaboration_contract_is_accepted() -> None:
    state, _ = state_and_request(
        DepartmentType.PROCUREMENT, "validate_procurement_purchase"
    )
    assert state.collaboration.request["receiver_department"] == "finance"
    assert "supplier_choice" not in state.collaboration.request["payload"]
