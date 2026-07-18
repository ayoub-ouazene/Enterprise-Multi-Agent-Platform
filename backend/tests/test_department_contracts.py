from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.departments.contracts import (
    DepartmentCollaborationRequest,
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    DepartmentToolRequest,
)


def result_values(**overrides):
    values = {
        "department_type": "it",
        "status": "completed",
        "decision": "placeholder_execution_completed",
        "reason": "IT execution foundation validated.",
        "user_message": "The IT placeholder completed its foundation check.",
        "current_stage": "it_placeholder_completed",
        "completed_step": "it_placeholder_completed",
        "next_action": "complete_request",
        "is_terminal": True,
        "safe_event_title": "IT stage completed",
        "safe_event_message": "IT execution foundation validated.",
    }
    values.update(overrides)
    return values


def context_values(**overrides):
    values = {
        "request_id": uuid4(),
        "company_id": uuid4(),
        "requester_user_id": uuid4(),
        "requester_employee_id": None,
        "owner_department_type": "it",
        "active_department_type": "it",
        "request_type": "hardware_request",
        "request_summary": "Employee requests a laptop.",
        "current_stage": "department_execution_started",
    }
    values.update(overrides)
    return values


def test_execution_context_is_strict_and_has_no_protected_credentials() -> None:
    context = DepartmentExecutionContext.model_validate(context_values())

    assert context.owner_department_type.value == "it"
    assert "database_url" not in DepartmentExecutionContext.model_fields
    assert "jwt" not in DepartmentExecutionContext.model_fields

    with pytest.raises(ValidationError):
        DepartmentExecutionContext.model_validate(
            context_values(owner_department_id=uuid4())
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"requires_review": True},
        {"requires_tool": True},
        {"status": "in_progress"},
        {"is_terminal": False},
        {"next_department": "finance"},
    ],
)
def test_contradictory_next_action_fields_are_rejected(changes) -> None:
    with pytest.raises(ValidationError, match="contradictory|requirement|only"):
        DepartmentExecutionResult.model_validate(result_values(**changes))


def test_tool_action_requires_exactly_one_tool_payload() -> None:
    tool = DepartmentToolRequest(
        tool_name="inventory_reader",
        operation="check_stock",
        arguments={"item_type": "laptop"},
        reason="Check existing stock before making a recommendation.",
        expected_result_type="inventory_summary",
    )
    result = DepartmentExecutionResult.model_validate(
        result_values(
            status="waiting_for_tool",
            next_action="execute_tool",
            is_terminal=False,
            requires_tool=True,
            tool_request=tool,
        )
    )

    assert result.tool_request == tool
    assert result.requires_collaboration is False


@pytest.mark.parametrize(
    "arguments",
    [
        {"shell_command": "whoami"},
        {"statement": "DROP TABLE users"},
        {"target_url": "https://example.test/private"},
    ],
)
def test_tool_contract_rejects_executable_content(arguments) -> None:
    with pytest.raises(ValidationError, match="executable"):
        DepartmentToolRequest(
            tool_name="future_tool",
            operation="future_operation",
            arguments=arguments,
            reason="Future-facing test.",
            expected_result_type="structured_result",
        )


def test_collaboration_contract_requires_distinct_supported_departments() -> None:
    request = DepartmentCollaborationRequest(
        request_id=uuid4(),
        sender_department="it",
        receiver_department="finance",
        action="validate_budget",
        payload={"estimated_cost": 500},
        expected_output={"decision": "approved_or_rejected"},
    )

    assert request.receiver_department.value == "finance"

    with pytest.raises(ValidationError, match="must differ"):
        DepartmentCollaborationRequest(
            request_id=uuid4(),
            sender_department="it",
            receiver_department="it",
            action="validate_budget",
        )


def test_protected_state_update_fields_are_impossible_to_address() -> None:
    with pytest.raises(ValidationError):
        DepartmentExecutionResult.model_validate(
            result_values(state_updates={"company_id": str(uuid4())})
        )
