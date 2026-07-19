import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4
from app.requests.enums import RequestStatus
from app.workflow.nodes.collaboration import department_collaboration_node
from app.workflow.state import WorkflowRequestState, WorkflowState


def test_customer_support_to_it_executes_same_request_id() -> None:
    request_id = uuid4()
    state = WorkflowState(request=WorkflowRequestState(request_id=request_id,
        company_id=uuid4(), requester_user_id=uuid4(), request_type="external_customer_incident",
        summary="Service error", status=RequestStatus.WAITING_FOR_DEPARTMENT))
    state.collaboration.request = {"request_id": str(request_id), "sender_department": "customer_support",
        "receiver_department": "it", "action": "diagnose_external_technical_issue",
        "payload": {"issue_summary": "Service error"}, "expected_output": {}}
    service = AsyncMock()
    service.execute_it_collaboration.return_value = SimpleNamespace(
        model_dump=lambda **kwargs: {"request_id": str(request_id), "sender_department": "customer_support",
            "receiver_department": "it", "action": "diagnose_external_technical_issue",
            "status": "completed", "result": {}, "reason": "Diagnosed"})
    runtime = SimpleNamespace(context=SimpleNamespace(department_execution_service=service))
    update = asyncio.run(department_collaboration_node(state, runtime))
    assert update["request"].request_id == request_id
    assert update["request"].status == RequestStatus.PROCESSING
    service.execute_it_collaboration.assert_awaited_once()


def test_it_finance_preparation_pauses_without_executing_finance() -> None:
    request_id = uuid4()
    state = WorkflowState(request=WorkflowRequestState(request_id=request_id,
        company_id=uuid4(), requester_user_id=uuid4(), request_type="hardware_request",
        summary="Laptop", status=RequestStatus.PROCESSING))
    state.collaboration.request = {"request_id": str(request_id), "sender_department": "it",
        "receiver_department": "finance", "action": "validate_it_purchase_budget",
        "payload": {}, "expected_output": {}}
    update = asyncio.run(department_collaboration_node(state, SimpleNamespace(context=None)))
    assert update["request"].status == RequestStatus.WAITING_FOR_DEPARTMENT
    assert update["request"].current_stage == "it_waiting_for_finance"
