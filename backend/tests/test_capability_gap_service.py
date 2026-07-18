import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.failures.enums import CapabilityGapStatus
from app.failures.repository import CapabilityGapRepository
from app.failures.schemas import CapabilityGapCreate, CapabilityGapStatusUpdate
from app.failures.service import (
    CapabilityGapService,
    FailurePermissionError,
    normalize_operation,
)
from app.notifications.service import NotificationService
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.users.repository import UserRepository
from app.workflow.service import WorkflowEventService


def context(actor=ActorType.COMPANY):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="user@example.com",
        actor_type=actor,
        is_manager=actor == ActorType.DEPARTMENT_MANAGER,
        department_id=uuid4() if actor == ActorType.DEPARTMENT_MANAGER else None,
    )


def fixture(current, request, gap):
    session = AsyncMock(spec=AsyncSession)
    repo = Mock(spec=CapabilityGapRepository)
    repo.create_or_increment = AsyncMock(return_value=(gap, True))
    repo.update_status = AsyncMock(return_value=gap)
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
    service = CapabilityGapService(
        session, current, repo, request_repo, events, notifications, users
    )
    return service, session, repo, request_repo, events, notifications


def test_operation_normalization_is_deterministic() -> None:
    assert (
        normalize_operation("  Export Customer Records ") == "export_customer_records"
    )
    assert normalize_operation("EXPORT--customer records") == "export_customer_records"


def test_gap_with_no_alternative_fails_request_and_notifies_atomically() -> None:
    current = context()
    request = SimpleNamespace(
        id=uuid4(),
        requester_user_id=uuid4(),
        status=RequestStatus.PROCESSING,
        owner_department_id=None,
        active_department_id=None,
    )
    gap = SimpleNamespace(id=uuid4())
    service, session, _, request_repo, events, notifications = fixture(
        current, request, gap
    )
    payload = CapabilityGapCreate(
        request_id=request.id,
        requested_operation="Export records",
        description="Unsupported operation",
        safe_user_message="This operation is not currently supported.",
    )
    result = asyncio.run(service.record(payload, no_alternative=True))
    assert result is gap
    assert request_repo.update.await_args.args[1]["status"] == RequestStatus.FAILED
    assert events.append.await_count == 2
    assert notifications.create.await_count == 2
    session.commit.assert_awaited_once()


def test_company_can_update_gap_status() -> None:
    current = context()
    gap = SimpleNamespace(id=uuid4())
    service, session, repo, *_ = fixture(current, None, gap)
    asyncio.run(
        service.update_status(
            gap.id,
            CapabilityGapStatusUpdate(
                status=CapabilityGapStatus.RESOLVED,
                resolution_notes="Planned capability delivered",
            ),
        )
    )
    assert (
        repo.update_status.await_args.kwargs["resolved_by_user_id"] == current.user_id
    )
    session.commit.assert_awaited_once()


def test_manager_cannot_update_gap_status() -> None:
    current = context(ActorType.DEPARTMENT_MANAGER)
    gap = SimpleNamespace(id=uuid4())
    service, _, repo, *_ = fixture(current, None, gap)
    with pytest.raises(FailurePermissionError):
        asyncio.run(
            service.update_status(
                gap.id, CapabilityGapStatusUpdate(status=CapabilityGapStatus.PLANNED)
            )
        )
    repo.update_status.assert_not_awaited()
