import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.failures.enums import FailureSource, FailureType
from app.failures.repository import FailureLogRepository
from app.failures.schemas import FailureCreate, FailureListFilters
from app.failures.service import FailurePermissionError, FailureService
from app.notifications.service import NotificationService
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.users.repository import UserRepository
from app.workflow.service import WorkflowEventService


def user(actor=ActorType.COMPANY, department_id=None):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="user@example.com",
        actor_type=actor,
        employee_id=uuid4() if department_id else None,
        department_id=department_id,
        is_manager=actor == ActorType.DEPARTMENT_MANAGER,
    )


def payload(request_id, terminal=True):
    return FailureCreate(
        request_id=request_id,
        failure_type=FailureType.DATABASE_FAILURE,
        failure_source=FailureSource.REPOSITORY,
        failed_operation="read_inventory",
        internal_message="sanitized diagnostic",
        safe_message="A required service is unavailable.",
        is_terminal=terminal,
    )


def fixture(current_user, request, failure):
    session = AsyncMock(spec=AsyncSession)
    repo = Mock(spec=FailureLogRepository)
    repo.create = AsyncMock(return_value=failure)
    repo.list = AsyncMock(return_value=[])
    repo.get_by_id = AsyncMock(return_value=failure)
    request_repo = Mock(spec=BusinessRequestRepository)
    request_repo.get_by_id = AsyncMock(return_value=request)
    request_repo.update = AsyncMock(return_value=request)
    events = Mock(spec=WorkflowEventService)
    events.append = AsyncMock()
    notifications = Mock(spec=NotificationService)
    notifications.create = AsyncMock()
    users = Mock(spec=UserRepository)
    users.list_department_managers = AsyncMock(return_value=[])
    users.list_company_accounts = AsyncMock(return_value=[SimpleNamespace(id=uuid4())])
    service = FailureService(
        session, current_user, repo, request_repo, events, notifications, users
    )
    return service, session, repo, request_repo, events, notifications


def test_terminal_failure_updates_request_event_log_and_notifications_atomically() -> (
    None
):
    current = user()
    request = SimpleNamespace(
        id=uuid4(),
        requester_user_id=uuid4(),
        status=RequestStatus.PROCESSING,
        owner_department_id=None,
        active_department_id=None,
    )
    failure = SimpleNamespace(id=uuid4())
    service, session, _, request_repo, events, notifications = fixture(
        current, request, failure
    )
    result = asyncio.run(service.record(payload(request.id), terminate_request=True))
    assert result is failure
    values = request_repo.update.await_args.args[1]
    assert values["status"] == RequestStatus.FAILED
    assert values["failed_at"].tzinfo is not None
    assert events.append.await_count == 1
    assert notifications.create.await_count == 2
    session.commit.assert_awaited_once()


def test_terminal_failure_rolls_back_when_logging_fails() -> None:
    current = user()
    request = SimpleNamespace(
        id=uuid4(),
        requester_user_id=uuid4(),
        status=RequestStatus.PROCESSING,
        owner_department_id=None,
        active_department_id=None,
    )
    service, session, repo, request_repo, events, _ = fixture(current, request, None)
    with pytest.raises(Exception):
        asyncio.run(service.record(payload(request.id), terminate_request=True))
    request_repo.update.assert_awaited_once()
    events.append.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_manager_failure_listing_is_department_scoped() -> None:
    department_id = uuid4()
    current = user(ActorType.DEPARTMENT_MANAGER, department_id)
    service, _, repo, *_ = fixture(current, None, None)
    asyncio.run(service.list(FailureListFilters()))
    assert repo.list.await_args.kwargs["department_id"] == department_id


def test_employee_cannot_access_failure_logs() -> None:
    current = user(ActorType.EMPLOYEE)
    service, _, _, *_ = fixture(current, None, None)
    with pytest.raises(FailurePermissionError):
        asyncio.run(service.list(FailureListFilters()))
