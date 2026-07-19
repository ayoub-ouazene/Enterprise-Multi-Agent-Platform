import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import NotFoundError
from app.database.base import Base
from app.departments.contracts import DepartmentExecutionResult
from app.departments.exceptions import (
    DepartmentContextMismatchError,
    DepartmentResultValidationError,
    DepartmentStateUpdateError,
)
from app.departments.execution import DepartmentExecutionService
from app.departments.registry import DepartmentRegistry
from app.departments.repository import DepartmentRepository
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.workflow.state import build_initial_workflow_state


def user(company_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="company@example.com",
        actor_type=ActorType.COMPANY,
    )


def execution_fixture(*, agent=None, active_type=DepartmentType.IT):
    current = user()
    owner_id = uuid4()
    active_id = owner_id if active_type == DepartmentType.IT else uuid4()
    business_request = SimpleNamespace(
        id=uuid4(),
        company_id=current.company_id,
        requester_user_id=uuid4(),
        requester_employee_id=uuid4(),
        request_type="hardware_request",
        owner_department_id=owner_id,
        active_department_id=active_id,
        status=RequestStatus.PROCESSING,
        current_stage="department_execution_started",
        summary="Employee requests a laptop.",
        workflow_state={},
        custom_data={"asset_category": "laptop"},
    )
    state = build_initial_workflow_state(business_request)
    state.routing.selected_department = DepartmentType.IT
    state.planning.current_plan = ["validate_request"]
    state.planning.pending_steps = ["complete_request"]

    owner = SimpleNamespace(
        id=owner_id,
        company_id=current.company_id,
        department_type=DepartmentType.IT,
        is_active=True,
    )
    active = SimpleNamespace(
        id=active_id,
        company_id=current.company_id,
        department_type=active_type,
        is_active=True,
    )
    requests = Mock(spec=BusinessRequestRepository)
    requests.get_by_id = AsyncMock(return_value=business_request)
    departments = Mock(spec=DepartmentRepository)
    departments.get_by_id = AsyncMock(
        side_effect=lambda department_id: owner if department_id == owner_id else active
    )
    implementation = agent or RecordingAgent()
    registry = DepartmentRegistry([implementation])
    service = DepartmentExecutionService(
        AsyncMock(),
        current,
        request_repository=requests,
        department_repository=departments,
        registry=registry,
    )
    return service, state, business_request, implementation, requests, departments


def valid_result(**overrides):
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
    return DepartmentExecutionResult.model_validate(values)


class RecordingAgent:
    department_type = DepartmentType.IT

    def __init__(self, result=None):
        self.result = result or valid_result()
        self.context = None

    async def execute(self, context):
        self.context = context
        return self.result


def test_context_is_built_from_trusted_tenant_request_and_state() -> None:
    service, state, request, agent, requests, departments = execution_fixture()

    update = asyncio.run(service.execute(state))

    assert agent.context.request_id == request.id
    assert agent.context.company_id == request.company_id
    assert agent.context.requester_user_id == request.requester_user_id
    assert agent.context.owner_department_type == DepartmentType.IT
    assert agent.context.active_department_type == DepartmentType.IT
    assert agent.context.relevant_custom_data == {"asset_category": "laptop"}
    assert update["request"].company_id == state.request.company_id
    assert update["request"].owner_department_id == state.request.owner_department_id
    requests.get_by_id.assert_awaited_once_with(state.request.request_id)
    assert departments.get_by_id.await_count == 2


def test_correct_registered_department_executes_without_client_choice() -> None:
    service, state, _, agent, _, _ = execution_fixture()

    update = asyncio.run(service.execute(state))

    assert agent.context.active_department_type == DepartmentType.IT
    assert update["execution"].department_result["department_type"] == "it"


def test_active_department_mismatch_is_rejected_before_agent_execution() -> None:
    service, state, _, agent, _, _ = execution_fixture(
        active_type=DepartmentType.FINANCE
    )

    with pytest.raises(DepartmentContextMismatchError, match="must match"):
        asyncio.run(service.execute(state))

    assert agent.context is None


def test_inactive_department_is_rejected_before_agent_execution() -> None:
    service, state, _, agent, _, departments = execution_fixture()
    inactive = SimpleNamespace(
        id=state.request.owner_department_id,
        company_id=state.request.company_id,
        department_type=DepartmentType.IT,
        is_active=False,
    )
    departments.get_by_id.return_value = inactive
    departments.get_by_id.side_effect = None

    with pytest.raises(DepartmentContextMismatchError, match="unavailable"):
        asyncio.run(service.execute(state))

    assert agent.context is None


def test_cross_company_request_behaves_as_not_found() -> None:
    service, state, _, _, requests, _ = execution_fixture()
    requests.get_by_id.return_value = None

    with pytest.raises(NotFoundError, match="Business request not found"):
        asyncio.run(service.execute(state))


def test_cross_company_department_reference_behaves_as_not_found() -> None:
    service, state, _, _, _, departments = execution_fixture()
    foreign_department = SimpleNamespace(
        id=state.request.owner_department_id,
        company_id=uuid4(),
        department_type=DepartmentType.IT,
        is_active=True,
    )
    departments.get_by_id.return_value = foreign_department
    departments.get_by_id.side_effect = None

    with pytest.raises(NotFoundError, match="Department not found"):
        asyncio.run(service.execute(state))


def test_malformed_department_result_is_rejected() -> None:
    agent = RecordingAgent()
    agent.result = {"department_type": "it", "unexpected": "raw output"}
    service, state, _, _, _, _ = execution_fixture(agent=agent)

    with pytest.raises(DepartmentResultValidationError, match="invalid structured"):
        asyncio.run(service.execute(state))


def test_result_from_wrong_department_is_rejected() -> None:
    agent = RecordingAgent(valid_result(department_type="finance"))
    service, state, _, _, _, _ = execution_fixture(agent=agent)

    with pytest.raises(DepartmentResultValidationError, match="active department"):
        asyncio.run(service.execute(state))


def test_allowed_updates_merge_without_changing_identity_or_owner() -> None:
    result = valid_result(
        state_updates={
            "planning": {
                "current_plan": ["validated"],
                "pending_steps": ["complete_request"],
                "current_step": "complete_request",
            },
            "execution": {
                "last_operation": "foundation_validation",
                "last_operation_status": "completed",
            },
        }
    )
    service, state, _, _, _, _ = execution_fixture(agent=RecordingAgent(result))

    update = asyncio.run(service.execute(state))
    merged = state.model_copy(
        update=update,
    )

    assert merged.request.request_id == state.request.request_id
    assert merged.request.company_id == state.request.company_id
    assert merged.request.requester_user_id == state.request.requester_user_id
    assert merged.request.owner_department_id == state.request.owner_department_id
    assert merged.planning.current_plan == ["validated"]
    assert "it_placeholder_completed" in merged.planning.completed_steps
    assert merged.execution.last_operation == "foundation_validation"


def test_completed_step_cannot_be_reintroduced_as_pending() -> None:
    result = valid_result(
        state_updates={"planning": {"pending_steps": ["it_placeholder_completed"]}}
    )
    service, state, _, _, _, _ = execution_fixture(agent=RecordingAgent(result))

    with pytest.raises(DepartmentStateUpdateError, match="cannot remain pending"):
        asyncio.run(service.execute(state))


def test_no_permanent_department_messages_table_exists() -> None:
    assert "department_messages" not in Base.metadata.tables
    assert "collaboration_messages" not in Base.metadata.tables
