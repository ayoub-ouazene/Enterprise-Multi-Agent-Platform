import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.notifications.service import NotificationService
from app.requests.enums import RequestPriority, RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.requests.schemas import BusinessRequestCreate, BusinessRequestListFilters
from app.requests.service import (
    BusinessRequestService,
    CancellationNotAllowedError,
    InvalidStatusTransitionError,
)
from app.workflow.enums import WorkflowEventType
from app.workflow.service import WorkflowEventService


def context(
    actor_type: ActorType,
    *,
    company_id=None,
    user_id=None,
    department_id=None,
) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=user_id or uuid4(),
        company_id=company_id or uuid4(),
        email="user@example.com",
        actor_type=actor_type,
        employee_id=uuid4() if actor_type != ActorType.EXTERNAL_USER else None,
        department_id=department_id,
        is_manager=actor_type == ActorType.DEPARTMENT_MANAGER,
    )


def request_record(current_user: AuthenticatedUser, **overrides):
    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "company_id": current_user.company_id,
        "requester_user_id": current_user.user_id,
        "requester_employee_id": current_user.employee_id,
        "owner_department_id": None,
        "active_department_id": None,
        "request_type": "software_access",
        "title": "Access request",
        "summary": "Access is needed.",
        "status": RequestStatus.CREATED,
        "current_stage": "request_received",
        "priority": RequestPriority.NORMAL,
        "workflow_state": {},
        "custom_data": {},
        "final_decision": None,
        "final_reason": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "cancelled_at": None,
        "failed_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def service_fixture(current_user: AuthenticatedUser, record=None):
    session = AsyncMock(spec=AsyncSession)
    repository = Mock(spec=BusinessRequestRepository)
    repository.create = AsyncMock(return_value=record)
    repository.get_by_id = AsyncMock(return_value=record)
    repository.list = AsyncMock(return_value=[])
    repository.update = AsyncMock(return_value=record)
    workflow_event_service = Mock(spec=WorkflowEventService)
    workflow_event_service.append = AsyncMock()
    notification_service = Mock(spec=NotificationService)
    notification_service.notify_request_created = AsyncMock()
    notification_service.notify_request_cancelled = AsyncMock()
    service = BusinessRequestService(
        session,
        current_user,
        repository,
        workflow_event_service,
        notification_service,
    )
    return service, session, repository


def test_create_uses_authenticated_context_and_initial_state() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, repository = service_fixture(current_user, record)
    payload = BusinessRequestCreate(
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
    )

    created = asyncio.run(service.create(payload))

    assert created.status == RequestStatus.CREATED
    assert created.owner_department_id is None
    assert created.active_department_id is None
    repository.create.assert_awaited_once_with(
        requester_user_id=current_user.user_id,
        requester_employee_id=current_user.employee_id,
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
        priority=RequestPriority.NORMAL,
        workflow_state={},
        custom_data={},
    )
    session.commit.assert_awaited_once()
    event_payload = service.workflow_event_service.append.await_args.args[1]
    assert event_payload.event_type == WorkflowEventType.REQUEST_CREATED
    assert service.workflow_event_service.append.await_args.kwargs == {"commit": False}
    service.notification_service.notify_request_created.assert_awaited_once_with(
        record,
        commit=False,
    )
    assert record.workflow_state["state_version"] == 1
    assert record.workflow_state["request"]["request_id"] == str(record.id)


def test_cross_company_get_behaves_as_not_found() -> None:
    current_user = context(ActorType.COMPANY)
    other_request = request_record(
        current_user,
        company_id=uuid4(),
    )
    service, _, _ = service_fixture(current_user, other_request)

    with pytest.raises(NotFoundError):
        asyncio.run(service.get(other_request.id))


def test_employee_list_is_restricted_to_their_requests() -> None:
    current_user = context(ActorType.EMPLOYEE)
    service, _, repository = service_fixture(current_user)

    asyncio.run(service.list(BusinessRequestListFilters()))

    assert (
        repository.list.await_args.kwargs["requester_user_id"] == current_user.user_id
    )
    assert repository.list.await_args.kwargs["department_id"] is None


def test_company_account_list_has_company_wide_visibility() -> None:
    current_user = context(ActorType.COMPANY)
    service, _, repository = service_fixture(current_user)

    asyncio.run(service.list(BusinessRequestListFilters()))

    assert repository.list.await_args.kwargs["requester_user_id"] is None
    assert repository.list.await_args.kwargs["department_id"] is None


def test_manager_list_includes_own_and_department_requests() -> None:
    department_id = uuid4()
    current_user = context(
        ActorType.DEPARTMENT_MANAGER,
        department_id=department_id,
    )
    service, _, repository = service_fixture(current_user)

    asyncio.run(service.list(BusinessRequestListFilters()))

    assert (
        repository.list.await_args.kwargs["requester_user_id"] == current_user.user_id
    )
    assert repository.list.await_args.kwargs["department_id"] == department_id


def test_manager_can_get_request_owned_by_their_department() -> None:
    department_id = uuid4()
    current_user = context(
        ActorType.DEPARTMENT_MANAGER,
        department_id=department_id,
    )
    record = request_record(
        current_user,
        requester_user_id=uuid4(),
        owner_department_id=department_id,
    )
    service, _, _ = service_fixture(current_user, record)

    assert asyncio.run(service.get(record.id)) is record


def test_valid_status_transition_is_persisted_by_service() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user, status=RequestStatus.CREATED)
    service, session, repository = service_fixture(current_user, record)

    asyncio.run(service.transition_status(record.id, RequestStatus.ROUTING))

    values = repository.update.await_args.args[1]
    assert values["status"] == RequestStatus.ROUTING
    assert values["current_stage"] == RequestStatus.ROUTING.value
    session.commit.assert_awaited_once()
    event_payload = service.workflow_event_service.append.await_args.args[1]
    assert event_payload.event_type == WorkflowEventType.ROUTING_STARTED


def test_invalid_status_transition_is_rejected() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user, status=RequestStatus.CREATED)
    service, session, repository = service_fixture(current_user, record)

    with pytest.raises(InvalidStatusTransitionError):
        asyncio.run(service.transition_status(record.id, RequestStatus.COMPLETED))

    repository.update.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_terminal_status_cannot_transition() -> None:
    current_user = context(ActorType.COMPANY)
    record = request_record(
        current_user,
        status=RequestStatus.COMPLETED,
        completed_at=datetime.now(UTC),
    )
    service, _, repository = service_fixture(current_user, record)

    with pytest.raises(InvalidStatusTransitionError):
        asyncio.run(service.transition_status(record.id, RequestStatus.PROCESSING))

    repository.update.assert_not_awaited()


def test_successful_cancellation_records_timestamp_and_safe_reason() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, repository = service_fixture(current_user, record)

    asyncio.run(service.cancel(record.id))

    values = repository.update.await_args.args[1]
    assert values["status"] == RequestStatus.CANCELLED
    assert values["cancelled_at"].tzinfo is not None
    assert values["final_reason"] == "Cancelled by requester"
    session.commit.assert_awaited_once()
    event_payload = service.workflow_event_service.append.await_args.args[1]
    assert event_payload.event_type == WorkflowEventType.REQUEST_CANCELLED
    service.notification_service.notify_request_cancelled.assert_awaited_once_with(
        record,
        commit=False,
    )


def test_cancelled_transition_uses_full_cancellation_policy() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, _, repository = service_fixture(current_user, record)

    asyncio.run(service.transition_status(record.id, RequestStatus.CANCELLED))

    values = repository.update.await_args.args[1]
    assert values["status"] == RequestStatus.CANCELLED
    assert values["final_reason"] == "Cancelled by requester"


def test_terminal_request_cancellation_is_rejected() -> None:
    current_user = context(ActorType.COMPANY)
    record = request_record(
        current_user,
        status=RequestStatus.FAILED,
    )
    service, session, repository = service_fixture(current_user, record)

    with pytest.raises(CancellationNotAllowedError):
        asyncio.run(service.cancel(record.id))

    repository.update.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_cancellation_after_irreversible_operation_is_rejected() -> None:
    current_user = context(ActorType.COMPANY)
    record = request_record(
        current_user,
        workflow_state={"execution": {"irreversible_operation_completed": True}},
    )
    service, session, repository = service_fixture(current_user, record)

    with pytest.raises(CancellationNotAllowedError):
        asyncio.run(service.cancel(record.id))

    repository.update.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_service_rolls_back_when_create_fails() -> None:
    current_user = context(ActorType.COMPANY)
    service, session, repository = service_fixture(current_user)
    repository.create.side_effect = RuntimeError("simulated persistence failure")
    payload = BusinessRequestCreate(
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
    )

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        asyncio.run(service.create(payload))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_request_creation_rolls_back_when_event_creation_fails() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, _ = service_fixture(current_user, record)
    service.workflow_event_service.append.side_effect = RuntimeError(
        "simulated event failure"
    )
    payload = BusinessRequestCreate(
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
    )

    with pytest.raises(RuntimeError, match="simulated event failure"):
        asyncio.run(service.create(payload))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_cancellation_rolls_back_when_event_creation_fails() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, repository = service_fixture(current_user, record)
    service.workflow_event_service.append.side_effect = RuntimeError(
        "simulated event failure"
    )

    with pytest.raises(RuntimeError, match="simulated event failure"):
        asyncio.run(service.cancel(record.id))

    repository.update.assert_awaited_once()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_request_creation_rolls_back_when_notification_creation_fails() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, _ = service_fixture(current_user, record)
    service.notification_service.notify_request_created.side_effect = RuntimeError(
        "simulated notification failure"
    )
    payload = BusinessRequestCreate(
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
    )

    with pytest.raises(RuntimeError, match="simulated notification failure"):
        asyncio.run(service.create(payload))

    service.workflow_event_service.append.assert_awaited_once()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_cancellation_rolls_back_when_notification_creation_fails() -> None:
    current_user = context(ActorType.EMPLOYEE)
    record = request_record(current_user)
    service, session, repository = service_fixture(current_user, record)
    service.notification_service.notify_request_cancelled.side_effect = RuntimeError(
        "simulated notification failure"
    )

    with pytest.raises(RuntimeError, match="simulated notification failure"):
        asyncio.run(service.cancel(record.id))

    repository.update.assert_awaited_once()
    service.workflow_event_service.append.assert_awaited_once()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
