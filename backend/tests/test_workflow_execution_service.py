import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import NotFoundError
from app.departments.repository import DepartmentRepository
from app.departments.contracts import DepartmentExecutionResult
from app.departments.execution import DepartmentExecutionService
from app.notifications.service import NotificationService
from app.llm.exceptions import FinanceOutputError, RouterProviderError
from app.requests.enums import RequestStatus
from app.workflow.enums import WorkflowEventType
from app.workflow.enums import WorkflowEventActorType
from app.workflow.exceptions import (
    WorkflowAlreadyStartedError,
    WorkflowExecutionFailedError,
    WorkflowNotStartedError,
    WorkflowPermissionError,
    WorkflowTerminalError,
)
from app.workflow.graph import workflow_graph
from app.workflow.persistence import WorkflowPersistence
from app.workflow.router_output import RouterOutput
from app.workflow.service import WorkflowEventService, WorkflowService
from app.workflow.state import (
    DEPARTMENT_STARTED_STEP,
    INITIALIZED_STEP,
    ROUTED_STEP,
    WORKFLOW_STARTED_STEP,
    WorkflowState,
    build_initial_workflow_state,
)


def user(actor=ActorType.COMPANY, *, company_id=None, department_id=None):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="user@example.com",
        actor_type=actor,
        employee_id=uuid4() if department_id else None,
        department_id=department_id,
        is_manager=actor == ActorType.DEPARTMENT_MANAGER,
    )


def request_record(current_user, **overrides):
    values = {
        "id": uuid4(),
        "company_id": current_user.company_id,
        "requester_user_id": uuid4(),
        "requester_employee_id": None,
        "request_type": "test_it_request",
        "owner_department_id": None,
        "active_department_id": None,
        "status": RequestStatus.CREATED,
        "current_stage": "request_received",
        "summary": "Run a deterministic test workflow.",
        "workflow_state": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def routed_output() -> RouterOutput:
    return RouterOutput(
        message_category="business_request",
        owner_department="it",
        confidence="high",
        needs_clarification=False,
        clarification_question=None,
        platform_answer=None,
        request_type="hardware_request",
        short_summary="Employee requests new hardware.",
        routing_reason="Hardware requests belong to IT.",
        unsupported_reason=None,
        is_capability_gap=False,
    )


class FakeRouterClient:
    clarification_maximum = 3

    def validate_configuration(self) -> None:
        return None

    async def classify(self, *args, **kwargs) -> RouterOutput:
        return routed_output()


class FakeDepartmentExecutionService:
    async def execute(self, state):
        result = DepartmentExecutionResult(
            department_type="it",
            status="completed",
            decision="placeholder_execution_completed",
            reason="IT execution foundation validated.",
            user_message="The IT placeholder completed its foundation check.",
            current_stage="it_placeholder_completed",
            completed_step="it_placeholder_completed",
            next_action="complete_request",
            is_terminal=True,
            safe_event_title="IT stage completed",
            safe_event_message="IT execution foundation validated.",
        )
        return DepartmentExecutionService._safe_state_update(state, result)


class FailingDepartmentExecutionService:
    async def execute(self, state):
        raise RuntimeError("internal department implementation details")


class InvalidFinanceExecutionService:
    async def execute(self, state):
        raise FinanceOutputError("raw malformed provider output")


def service_fixture(current_user, request, *, graph=workflow_graph, state=None):
    session = AsyncMock(spec=AsyncSession)
    persistence = Mock(spec=WorkflowPersistence)
    persistence.load_request = AsyncMock(return_value=request)
    loaded_state = state
    if loaded_state is None and request is not None:
        loaded_state = build_initial_workflow_state(request)
    persistence.load_state = Mock(return_value=loaded_state)
    persistence.save_checkpoint = AsyncMock(return_value=request)
    departments = Mock(spec=DepartmentRepository)
    department = SimpleNamespace(
        id=uuid4(),
        department_type=DepartmentType.IT,
        is_active=True,
    )
    departments.list = AsyncMock(return_value=[department])
    events = Mock(spec=WorkflowEventService)
    events.append = AsyncMock()
    notifications = Mock(spec=NotificationService)
    notifications.notify_terminal_request = AsyncMock()
    failures = Mock()
    failures.record = AsyncMock(return_value=SimpleNamespace(id=uuid4()))
    service = WorkflowService(
        session,
        current_user,
        persistence=persistence,
        department_repository=departments,
        department_execution_service=FakeDepartmentExecutionService(),
        workflow_event_service=events,
        notification_service=notifications,
        failure_service=failures,
        capability_gap_service=Mock(),
        router_client=FakeRouterClient(),
        graph=graph,
    )
    return service, session, persistence, departments, events, notifications, failures


def event_types(events) -> list[WorkflowEventType]:
    return [call.args[1].event_type for call in events.append.await_args_list]


def test_workflow_start_persists_ordered_events_and_completion_notification() -> None:
    current = user()
    request = request_record(current)
    service, session, persistence, departments, events, notifications, _ = (
        service_fixture(current, request)
    )

    result = asyncio.run(service.start(request.id))

    assert result.status == RequestStatus.COMPLETED
    assert result.owner_department_id == departments.list.return_value[0].id
    assert event_types(events) == [
        WorkflowEventType.ROUTING_STARTED,
        WorkflowEventType.REQUEST_ROUTED,
        WorkflowEventType.STAGE_STARTED,
        WorkflowEventType.STAGE_COMPLETED,
        WorkflowEventType.REQUEST_COMPLETED,
    ]
    assert persistence.save_checkpoint.await_count == 6
    notifications.notify_terminal_request.assert_awaited_once()
    assert session.commit.await_count == 6
    stage_started = events.append.await_args_list[2].args[1]
    stage_completed = events.append.await_args_list[3].args[1]
    completion = events.append.await_args_list[4].args[1]
    assert stage_started.actor_type == WorkflowEventActorType.DEPARTMENT_AGENT
    assert stage_completed.actor_type == WorkflowEventActorType.DEPARTMENT_AGENT
    assert stage_completed.title == "IT stage completed"
    assert completion.actor_type == WorkflowEventActorType.SYSTEM


def test_cross_company_start_behaves_as_not_found() -> None:
    current = user()
    service, session, persistence, _, events, _, _ = service_fixture(current, None)
    persistence.load_request.return_value = None

    with pytest.raises(NotFoundError):
        asyncio.run(service.start(uuid4()))

    events.append.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_start_rejects_terminal_request_without_side_effects() -> None:
    current = user()
    request = request_record(current, status=RequestStatus.COMPLETED)
    service, _, persistence, _, events, notifications, _ = service_fixture(
        current, request
    )

    with pytest.raises(WorkflowTerminalError):
        asyncio.run(service.start(request.id))

    persistence.save_checkpoint.assert_not_awaited()
    events.append.assert_not_awaited()
    notifications.notify_terminal_request.assert_not_awaited()


def test_duplicate_start_does_not_duplicate_events_or_notifications() -> None:
    current = user()
    request = request_record(current, status=RequestStatus.ROUTING)
    service, _, persistence, _, events, notifications, _ = service_fixture(
        current, request
    )

    with pytest.raises(WorkflowAlreadyStartedError):
        asyncio.run(service.start(request.id))

    persistence.save_checkpoint.assert_not_awaited()
    events.append.assert_not_awaited()
    notifications.notify_terminal_request.assert_not_awaited()


def test_router_configuration_is_checked_before_start_checkpoint() -> None:
    current = user()
    request = request_record(current, request_type="software_access")
    service, _, persistence, _, events, _, _ = service_fixture(current, request)
    service.router_client = None

    from app.llm.exceptions import RouterConfigurationError

    with pytest.raises(RouterConfigurationError):
        asyncio.run(service.start(request.id))

    persistence.save_checkpoint.assert_not_awaited()
    events.append.assert_not_awaited()


def test_requester_cannot_control_workflow() -> None:
    current = user(ActorType.EMPLOYEE)
    request = request_record(current)
    service, _, persistence, _, _, _, _ = service_fixture(current, request)

    with pytest.raises(WorkflowPermissionError):
        asyncio.run(service.start(request.id))

    persistence.load_state.assert_not_called()


def test_manager_must_control_request_in_own_department() -> None:
    current = user(ActorType.DEPARTMENT_MANAGER, department_id=uuid4())
    request = request_record(current, owner_department_id=uuid4())
    service, _, _, _, _, _, _ = service_fixture(current, request)

    with pytest.raises(WorkflowPermissionError):
        asyncio.run(service.start(request.id))


def test_resume_loads_state_and_skips_completed_steps() -> None:
    current = user()
    department_id = uuid4()
    request = request_record(
        current,
        status=RequestStatus.PROCESSING,
        current_stage="placeholder_department_processing",
        owner_department_id=department_id,
        active_department_id=department_id,
    )
    state = build_initial_workflow_state(request)
    state.planning.completed_steps = [
        WORKFLOW_STARTED_STEP,
        INITIALIZED_STEP,
        ROUTED_STEP,
        DEPARTMENT_STARTED_STEP,
    ]
    state.planning.current_step = "placeholder_department"
    service, _, persistence, _, events, notifications, _ = service_fixture(
        current,
        request,
        state=state,
    )

    result = asyncio.run(service.resume(request.id))

    assert result.status == RequestStatus.COMPLETED
    persistence.load_state.assert_called_once_with(request)
    assert event_types(events) == [
        WorkflowEventType.REQUEST_RESUMED,
        WorkflowEventType.STAGE_COMPLETED,
        WorkflowEventType.REQUEST_COMPLETED,
    ]
    assert WorkflowEventType.REQUEST_ROUTED not in event_types(events)
    assert WorkflowEventType.STAGE_STARTED not in event_types(events)
    notifications.notify_terminal_request.assert_awaited_once()


def test_resume_of_created_request_is_rejected() -> None:
    current = user()
    request = request_record(current)
    service, _, _, _, _, _, _ = service_fixture(current, request)

    with pytest.raises(WorkflowNotStartedError):
        asyncio.run(service.resume(request.id))


def test_resume_of_terminal_request_is_rejected() -> None:
    current = user()
    request = request_record(current, status=RequestStatus.FAILED)
    service, _, _, _, _, _, _ = service_fixture(current, request)

    with pytest.raises(WorkflowTerminalError):
        asyncio.run(service.resume(request.id))


class FailingGraph:
    async def astream(self, *args, **kwargs):
        raise RuntimeError("simulated graph node exception")
        yield


class FailedRouterClient(FakeRouterClient):
    async def classify(self, *args, **kwargs) -> RouterOutput:
        raise RouterProviderError("provider headers and internals")


def test_graph_failure_uses_atomic_existing_failure_service() -> None:
    current = user()
    request = request_record(current)
    service, session, persistence, _, events, notifications, failures = service_fixture(
        current, request, graph=FailingGraph()
    )

    with pytest.raises(WorkflowExecutionFailedError):
        asyncio.run(service.start(request.id))

    failures.record.assert_awaited_once()
    assert failures.record.await_args.kwargs == {
        "terminate_request": True,
        "commit": False,
    }
    failed_state: WorkflowState = persistence.save_checkpoint.await_args_list[-1].args[
        0
    ]
    assert failed_state.request.status == RequestStatus.FAILED
    assert failed_state.failure.has_failure is True
    assert failed_state.failure.terminal is True
    assert "simulated graph node exception" not in failed_state.failure.safe_message
    assert event_types(events) == [WorkflowEventType.ROUTING_STARTED]
    notifications.notify_terminal_request.assert_not_awaited()
    assert session.commit.await_count == 2


def test_terminal_router_provider_failure_uses_safe_failure_service() -> None:
    current = user()
    request = request_record(current)
    service, _, persistence, _, _, _, failures = service_fixture(current, request)
    service.router_client = FailedRouterClient()

    with pytest.raises(WorkflowExecutionFailedError):
        asyncio.run(service.start(request.id))

    failures.record.assert_awaited_once()
    failure_payload = failures.record.await_args.args[0]
    assert failure_payload.safe_message == (
        "The workflow could not be completed due to an internal processing error."
    )
    failed_state = persistence.save_checkpoint.await_args_list[-1].args[0]
    assert "provider headers" not in failed_state.failure.safe_message


def test_department_exception_uses_sanitized_terminal_failure_path() -> None:
    current = user()
    request = request_record(current)
    service, _, persistence, _, events, notifications, failures = service_fixture(
        current,
        request,
    )
    service.department_execution_service = FailingDepartmentExecutionService()

    with pytest.raises(WorkflowExecutionFailedError):
        asyncio.run(service.start(request.id))

    failures.record.assert_awaited_once()
    failed_state = persistence.save_checkpoint.await_args_list[-1].args[0]
    assert failed_state.request.status == RequestStatus.FAILED
    assert "implementation details" not in failed_state.failure.safe_message
    assert event_types(events) == [
        WorkflowEventType.ROUTING_STARTED,
        WorkflowEventType.REQUEST_ROUTED,
        WorkflowEventType.STAGE_STARTED,
    ]
    notifications.notify_terminal_request.assert_not_awaited()


def test_department_lookup_is_tenant_repository_call() -> None:
    current = user()
    request = request_record(current)
    service, _, _, departments, _, _, _ = service_fixture(current, request)

    asyncio.run(service.start(request.id))

    departments.list.assert_awaited_once_with()


def test_finance_output_failure_is_sanitized_through_failure_service() -> None:
    current = user()
    request = request_record(current)
    service, _, persistence, _, _, _, failures = service_fixture(current, request)
    service.department_execution_service = InvalidFinanceExecutionService()
    with pytest.raises(WorkflowExecutionFailedError):
        asyncio.run(service.start(request.id))
    payload = failures.record.await_args.args[0]
    assert payload.safe_message == "Finance could not validate its response."
    failed_state = persistence.save_checkpoint.await_args_list[-1].args[0]
    assert "malformed" not in failed_state.failure.safe_message
