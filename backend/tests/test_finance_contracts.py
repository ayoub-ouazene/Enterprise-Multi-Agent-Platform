from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.departments.finance.schemas import FinanceDepartmentResult


def valid_finance_result(**changes) -> FinanceDepartmentResult:
    values = {
        "category": "budget_inquiry",
        "decision": "answer",
        "reason": "The available trusted information was evaluated.",
        "user_message": "Finance completed the requested check.",
        "confidence": "high",
        "next_action": "complete_request",
        "safe_event_title": "Finance check completed",
        "safe_event_message": "Finance completed a controlled validation.",
    }
    values.update(changes)
    return FinanceDepartmentResult.model_validate(values)


def test_insufficient_budget_cannot_be_validated() -> None:
    with pytest.raises(ValidationError, match="insufficient"):
        valid_finance_result(
            decision="validated", budget_sufficient=False,
            requested_amount="50.00", currency="USD",
        )


def test_transaction_requires_payload_and_controlled_tool() -> None:
    with pytest.raises(ValidationError, match="transaction payload"):
        valid_finance_result(transaction_should_be_created=True)


def test_approval_cannot_complete_before_authorized_response() -> None:
    with pytest.raises(ValidationError, match="cannot complete"):
        valid_finance_result(
            decision="approval_required",
            approval_required=True,
            approval_reason="Threshold exceeded",
        )


def test_collaboration_result_preserves_request_and_department_direction() -> None:
    request_id = uuid4()
    result = valid_finance_result(
        decision="return_to_it",
        requires_it_return=True,
        it_collaboration_result={
            "request_id": str(request_id),
            "sender_department": "finance",
            "receiver_department": "it",
            "action": "validate_it_purchase_budget",
            "status": "completed",
            "result": {"budget_validated": True},
            "reason": "Budget validated",
        },
    )
    assert result.it_collaboration_result.request_id == request_id


def test_finance_information_requires_authorized_source() -> None:
    with pytest.raises(ValidationError, match="authorized evidence"):
        valid_finance_result(category="finance_information")


def test_human_approval_is_prepared_without_premature_approval() -> None:
    result = valid_finance_result(
        category="human_approval_required", decision="approval_required",
        approval_required=True, approval_reason="Configured threshold exceeded",
        requires_human_action=True,
        human_action_request={
            "action_type": "approve_finance_spending", "assigned_role": "company",
            "request_summary": "Approve 800 USD", "evidence_summary": "Policy threshold is 500 USD",
            "recommendation": "Approve only if the business reason is accepted",
            "exact_action_required": "Approve or reject the spending request",
            "reason": "Human financial authority is required",
        },
        next_action="request_human_action",
        state_updates={"approval_status": "pending"},
    )
    assert result.state_updates.approval_status.value == "pending"
    assert result.decision.value != "validated"
