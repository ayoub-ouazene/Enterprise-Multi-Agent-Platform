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
from app.requests.repository import BusinessRequestRepository
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.repository import WorkflowEventRepository
from app.workflow.schemas import WorkflowEventCreate
from app.workflow.service import WorkflowEventService


def context(actor_type, *, company_id=None, user_id=None, department_id=None):
    return AuthenticatedUser(
        user_id=user_id or uuid4(),
        company_id=company_id or uuid4(),
        email="user@example.com",
        actor_type=actor_type,
        employee_id=uuid4() if actor_type != ActorType.EXTERNAL_USER else None,
        department_id=department_id,
        is_manager=actor_type == ActorType.DEPARTMENT_MANAGER,
    )


def request_record(current_user, **overrides):
    values = {
        "id": uuid4(),
        "company_id": current_user.company_id,
        "requester_user_id": current_user.user_id,
        "owner_department_id": None,
        "active_department_id": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def event_record(request_id, visibility):
    return SimpleNamespace(
        id=uuid4(),
        request_id=request_id,
        event_type=WorkflowEventType.REQUEST_CREATED,
        stage="request_received",
        title="Request created",
        message="The request has been created.",
        actor_type=WorkflowEventActorType.USER,
        actor_user_id=uuid4(),
        department_id=None,
        visibility=visibility,
        event_data={},
        sequence_number=1,
        created_at=datetime.now(UTC),
    )


def service_fixture(current_user, request=None, events=None):
    session = AsyncMock(spec=AsyncSession)
    event_repository = Mock(spec=WorkflowEventRepository)
    event_repository.append = AsyncMock()
    event_repository.list_for_request = AsyncMock(return_value=events or [])
    request_repository = Mock(spec=BusinessRequestRepository)
    request_repository.get_by_id = AsyncMock(return_value=request)
    service = WorkflowEventService(
        session,
        current_user,
        event_repository,
        request_repository,
    )
    return service, session, event_repository, request_repository


def create_payload(actor_type=WorkflowEventActorType.USER):
    return WorkflowEventCreate(
        event_type=WorkflowEventType.REQUEST_CREATED,
        stage="request_received",
        title="Request created",
        message="The request has been created.",
        actor_type=actor_type,
        visibility=WorkflowEventVisibility.REQUESTER,
        event_data={},
    )


def test_append_derives_actor_user_and_commits_when_service_owns_operation() -> None:
    current_user = context(ActorType.EMPLOYEE)
    event = event_record(uuid4(), WorkflowEventVisibility.REQUESTER)
    service, session, repository, _ = service_fixture(current_user)
    repository.append.return_value = event

    result = asyncio.run(service.append(event.request_id, create_payload()))

    assert result is event
    assert repository.append.await_args.kwargs["actor_user_id"] == current_user.user_id
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(event)


def test_append_does_not_commit_when_part_of_larger_transaction() -> None:
    current_user = context(ActorType.COMPANY)
    event = event_record(uuid4(), WorkflowEventVisibility.REQUESTER)
    service, session, repository, _ = service_fixture(current_user)
    repository.append.return_value = event

    asyncio.run(service.append(event.request_id, create_payload(), commit=False))

    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


def test_cross_company_timeline_behaves_as_not_found() -> None:
    current_user = context(ActorType.EMPLOYEE)
    service, _, repository, _ = service_fixture(current_user, request=None)

    with pytest.raises(NotFoundError):
        asyncio.run(service.timeline(uuid4()))

    repository.list_for_request.assert_not_awaited()


@pytest.mark.parametrize(
    ("actor_type", "expected"),
    [
        (ActorType.EMPLOYEE, {WorkflowEventVisibility.REQUESTER}),
        (
            ActorType.DEPARTMENT_MANAGER,
            {
                WorkflowEventVisibility.REQUESTER,
                WorkflowEventVisibility.MANAGER,
            },
        ),
        (
            ActorType.COMPANY,
            {
                WorkflowEventVisibility.REQUESTER,
                WorkflowEventVisibility.MANAGER,
                WorkflowEventVisibility.COMPANY,
            },
        ),
    ],
)
def test_timeline_applies_role_visibility(actor_type, expected) -> None:
    department_id = uuid4() if actor_type == ActorType.DEPARTMENT_MANAGER else None
    current_user = context(actor_type, department_id=department_id)
    request = request_record(current_user)
    service, _, repository, _ = service_fixture(current_user, request=request)

    asyncio.run(service.timeline(request.id))

    assert repository.list_for_request.await_args.kwargs["visibilities"] == frozenset(
        expected
    )


def test_internal_event_is_defensively_removed_from_public_timeline() -> None:
    current_user = context(ActorType.COMPANY)
    request = request_record(current_user)
    public_event = event_record(request.id, WorkflowEventVisibility.COMPANY)
    internal_event = event_record(request.id, WorkflowEventVisibility.INTERNAL)
    service, _, _, _ = service_fixture(
        current_user,
        request=request,
        events=[public_event, internal_event],
    )

    timeline = asyncio.run(service.timeline(request.id))

    assert [item.id for item in timeline] == [public_event.id]
    assert "actor_user_id" not in timeline[0].model_dump()
    assert "visibility" not in timeline[0].model_dump()


def test_manager_must_still_be_authorized_for_the_request() -> None:
    current_user = context(ActorType.DEPARTMENT_MANAGER, department_id=uuid4())
    request = request_record(
        current_user,
        requester_user_id=uuid4(),
        owner_department_id=uuid4(),
    )
    service, _, repository, _ = service_fixture(current_user, request=request)

    with pytest.raises(NotFoundError):
        asyncio.run(service.timeline(request.id))

    repository.list_for_request.assert_not_awaited()
