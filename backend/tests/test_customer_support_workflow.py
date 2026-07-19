from uuid import uuid4

from app.departments.customer_support.schemas import CustomerSupportResult
from app.requests.enums import RequestStatus
from app.workflow.nodes.collaboration import customer_support_collaboration_node
from app.workflow.routing import route_after_department
from app.workflow.state import WorkflowRequestState, WorkflowState


def test_clarification_pauses_graph_without_terminal_completion() -> None:
    result = CustomerSupportResult.model_validate({
        "category": "troubleshooting", "answer": "I need the displayed error.",
        "decision": "clarify", "reason": "One diagnostic detail is missing.",
        "confidence": "medium", "needs_clarification": True,
        "clarification_question": "What exact error message do you see?",
        "next_action": "wait_for_user_input", "safe_event_title": "Information required",
        "safe_event_message": "Customer Support requested one diagnostic detail.",
    })
    state = WorkflowState(request=WorkflowRequestState(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        request_type="technical_issue", summary="Cannot sign in.", status=RequestStatus.PROCESSING,
    ))
    state.execution.department_result = {
        "department_type": "customer_support", "status": "waiting_for_user",
        "decision": "clarify", "reason": result.reason, "user_message": result.answer,
        "current_stage": "customer_support_waiting_for_customer",
        "completed_step": "customer_support_analysis_completed",
        "next_action": "wait_for_user_input", "is_terminal": False,
        "safe_event_title": result.safe_event_title, "safe_event_message": result.safe_event_message,
    }
    assert route_after_department(state) == "__end__"


def test_it_preparation_preserves_owner_and_request_id() -> None:
    request_id, company_id, owner_id = uuid4(), uuid4(), uuid4()
    state = WorkflowState(request=WorkflowRequestState(
        request_id=request_id, company_id=company_id, requester_user_id=uuid4(),
        request_type="technical_issue", summary="External service fails.",
        owner_department_id=owner_id, active_department_id=owner_id,
        status=RequestStatus.PROCESSING,
    ))
    state.collaboration.request = {"request_id": str(request_id),
        "sender_department": "customer_support", "receiver_department": "it",
        "action": "diagnose_external_technical_issue", "payload": {}, "expected_output": {}}
    update = customer_support_collaboration_node(state)
    assert update["request"].request_id == request_id
    assert update["request"].owner_department_id == owner_id
    assert update["request"].status == RequestStatus.WAITING_FOR_DEPARTMENT
