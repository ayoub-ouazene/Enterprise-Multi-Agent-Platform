from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.departments.it.schemas import ITDepartmentResult


def valid_it_result(**overrides):
    values = {"category": "it_information", "decision": "answer",
        "reason": "The authorized IT procedure answers the question.",
        "user_message": "Follow the documented company sign-in procedure.", "confidence": "high",
        "sources_used": [{"document_id": str(uuid4()), "title": "IT Access Guide",
            "document_type": "procedure", "version": 1, "chunk_index": 0}],
        "next_action": "complete_request", "safe_event_title": "IT question answered",
        "safe_event_message": "IT answered using authorized company knowledge."}
    values.update(overrides)
    return ITDepartmentResult.model_validate(values)


def test_it_information_requires_authorized_evidence() -> None:
    with pytest.raises(ValidationError, match="authorized evidence"):
        valid_it_result(sources_used=[])


def test_budget_and_supplier_actions_are_only_structured_collaboration() -> None:
    request_id = uuid4()
    result = valid_it_result(category="hardware_request", decision="prepare_finance",
        sources_used=[], requires_finance_collaboration=True, next_action="collaborate",
        finance_collaboration_request={"request_id": str(request_id), "sender_department": "it",
            "receiver_department": "finance", "action": "validate_it_purchase_budget",
            "payload": {}, "expected_output": {}})
    assert result.finance_collaboration_request.request_id == request_id
    with pytest.raises(ValidationError):
        valid_it_result(category="hardware_request", decision="prepare_finance", sources_used=[],
            requires_finance_collaboration=True, next_action="collaborate")


def test_resolved_incident_cannot_require_physical_action() -> None:
    with pytest.raises(ValidationError, match="resolved incident"):
        valid_it_result(category="employee_incident", decision="prepare_human_action",
            sources_used=[], incident_resolved=True, requires_human_action=True,
            next_action="request_human_action", human_action_request={"action_type": "onsite_repair",
                "assigned_role": "department_manager", "request_summary": "Device issue",
                "evidence_summary": "Remote checks complete", "recommendation": "Inspect device",
                "exact_action_required": "Perform onsite inspection", "reason": "Physical diagnosis required"})


def test_it_allows_only_one_concise_clarification() -> None:
    result = valid_it_result(category="account_unlock", decision="clarify", sources_used=[],
        needs_user_clarification=True, clarification_question="Which company account is locked?",
        next_action="wait_for_user_input")
    assert result.clarification_question.count("?") == 1
    with pytest.raises(ValidationError, match="one concise"):
        valid_it_result(category="account_unlock", decision="clarify", sources_used=[],
            needs_user_clarification=True, clarification_question="Which account? Which system?",
            next_action="wait_for_user_input")


def test_it_cannot_claim_access_or_physical_assignment_completed() -> None:
    with pytest.raises(ValidationError, match="provisioning completed"):
        valid_it_result(category="account_unlock", decision="prepare_operation", sources_used=[],
            state_updates={"access": {"employee_id": str(uuid4()), "access_type": "account_unlock",
                "target_system": "Identity", "business_reason": "Locked account",
                "provisioning_status": "completed"}})
    with pytest.raises(ValidationError, match="physical assignment completed"):
        valid_it_result(category="hardware_request", decision="prepare_operation", sources_used=[],
            state_updates={"hardware": {"employee_id": str(uuid4()), "asset_type": "laptop",
                "business_reason": "Work requirement", "assignment_status": "completed"}})


def test_human_technician_action_is_preparation_only() -> None:
    result = valid_it_result(category="human_technician_escalation",
        decision="prepare_human_action", sources_used=[], requires_human_action=True,
        next_action="request_human_action", human_action_request={"action_type": "onsite_diagnosis",
            "assigned_role": "department_manager", "request_summary": "Device issue",
            "evidence_summary": "Remote checks completed", "recommendation": "Inspect device",
            "exact_action_required": "Perform physical inspection", "reason": "Physical work required"})
    assert result.human_action_request.action_type == "onsite_diagnosis"
