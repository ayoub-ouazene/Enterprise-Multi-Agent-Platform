"""Human-action node supports all five predefined departments."""
from uuid import uuid4

import pytest
from types import SimpleNamespace

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionResult, DepartmentHumanActionRequest
from app.requests.enums import RequestStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.nodes.human_action import customer_support_human_action_node
from app.workflow.state import WorkflowState, build_initial_workflow_state


def _state(department_type: DepartmentType) -> WorkflowState:
    base = build_initial_workflow_state(
        SimpleNamespace(
            id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
            requester_employee_id=None, request_type="test", owner_department_id=None,
            active_department_id=None, status=RequestStatus.PROCESSING,
            current_stage="test_stage", summary="test",
        )
    )
    execution = base.execution.model_copy(update={
    "department_result": DepartmentExecutionResult(
        department_type=department_type,
        status="waiting_for_human",
        decision="pending_human",
        reason="test",
        user_message="test",
        current_stage="test",
        completed_step="test",
        next_action="request_human_action",
        is_terminal=False,
        safe_event_title="Human action test",
        safe_event_message="test",
        requires_human_action=True,
        human_action_request=DepartmentHumanActionRequest(
            action_type="approve_test",
            assigned_role="company",
            request_summary="Test human action.",
            evidence_summary="None.",
            recommendation="Approve.",
            exact_action_required="Approve.",
            reason="Test.",
        ),
    ).model_dump(mode="json")
    })
    return base.model_copy(update={"execution": execution})


@pytest.mark.parametrize("dept", [
    DepartmentType.CUSTOMER_SUPPORT,
    DepartmentType.IT,
    DepartmentType.FINANCE,
    DepartmentType.HR,
    DepartmentType.PROCUREMENT,
])
def test_human_action_node_accepts_all_departments(dept: DepartmentType) -> None:
    state = _state(dept)
    result = customer_support_human_action_node(state)
    assert result["request"].status == RequestStatus.WAITING_FOR_HUMAN_ACTION
    assert result["human_action"].required is True
    assert result["human_action"].status == "pending"


@pytest.mark.parametrize("dept,expected_stage", [
    (DepartmentType.CUSTOMER_SUPPORT, "customer_support_waiting_for_human_support"),
    (DepartmentType.IT, "it_waiting_for_technician"),
    (DepartmentType.FINANCE, "finance_waiting_for_approval"),
    (DepartmentType.HR, "hr_waiting_for_manager_approval"),
    (DepartmentType.PROCUREMENT, "procurement_waiting_for_selection"),
])
def test_human_action_node_preserves_correct_stage(dept: DepartmentType, expected_stage: str) -> None:
    state = _state(dept)
    result = customer_support_human_action_node(state)
    assert result["request"].current_stage == expected_stage
