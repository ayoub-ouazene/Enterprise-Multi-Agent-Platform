import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.workflow.exceptions import (
    InvalidWorkflowStateError,
    UnsupportedWorkflowStateVersionError,
    WorkflowPersistenceError,
)
from app.workflow.persistence import WorkflowPersistence
from app.workflow.state import build_initial_workflow_state


def current_user(company_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="company@example.com",
        actor_type=ActorType.COMPANY,
    )


def request_record(user: AuthenticatedUser, **overrides):
    values = {
        "id": uuid4(),
        "company_id": user.company_id,
        "requester_user_id": uuid4(),
        "requester_employee_id": None,
        "request_type": "test_it_request",
        "owner_department_id": None,
        "active_department_id": None,
        "status": RequestStatus.CREATED,
        "current_stage": "request_received",
        "summary": "Test persistence.",
        "workflow_state": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def fixture(user: AuthenticatedUser, request=None):
    session = AsyncMock(spec=AsyncSession)
    repository = Mock(spec=BusinessRequestRepository)
    repository.get_by_id = AsyncMock(return_value=request)
    repository.get_by_id_for_update = AsyncMock(return_value=request)
    repository.update = AsyncMock(return_value=request)
    return WorkflowPersistence(session, user, repository), repository


def test_empty_created_state_is_reconstructed_for_legacy_request() -> None:
    user = current_user()
    request = request_record(user)
    persistence, _ = fixture(user, request)

    state = persistence.load_state(request)

    assert state.request.request_id == request.id
    assert state.state_version == 1


def test_nonempty_unversioned_state_is_rejected() -> None:
    user = current_user()
    request = request_record(user, workflow_state={"request": {}})
    persistence, _ = fixture(user, request)

    with pytest.raises(InvalidWorkflowStateError, match="no version"):
        persistence.load_state(request)


def test_unsupported_future_state_version_is_rejected() -> None:
    user = current_user()
    request = request_record(user, workflow_state={"state_version": 99})
    persistence, _ = fixture(user, request)

    with pytest.raises(UnsupportedWorkflowStateVersionError):
        persistence.load_state(request)


def test_state_with_mismatched_company_is_rejected() -> None:
    user = current_user()
    request = request_record(user)
    state = build_initial_workflow_state(request).to_storage()
    state["request"]["company_id"] = str(uuid4())
    request.workflow_state = state
    persistence, _ = fixture(user, request)

    with pytest.raises(InvalidWorkflowStateError, match="does not match"):
        persistence.load_state(request)


def test_for_update_load_uses_tenant_repository_lock() -> None:
    user = current_user()
    request = request_record(user)
    persistence, repository = fixture(user, request)

    result = asyncio.run(persistence.load_request(request.id, for_update=True))

    assert result is request
    repository.get_by_id_for_update.assert_awaited_once_with(request.id)


def test_save_checkpoint_updates_state_and_request_columns_without_commit() -> None:
    user = current_user()
    request = request_record(user)
    persistence, repository = fixture(user, request)
    state = build_initial_workflow_state(request)

    result = asyncio.run(persistence.save_checkpoint(state))

    assert result is request
    values = repository.update.await_args.args[1]
    assert values["workflow_state"]["state_version"] == 1
    assert values["status"] == RequestStatus.CREATED
    assert values["current_stage"] == "request_received"
    assert "commit" not in repository.update.await_args.kwargs


def test_save_checkpoint_wraps_repository_failure() -> None:
    user = current_user()
    request = request_record(user)
    persistence, repository = fixture(user, request)
    repository.update.side_effect = RuntimeError("database unavailable")

    with pytest.raises(WorkflowPersistenceError):
        asyncio.run(persistence.save_checkpoint(build_initial_workflow_state(request)))
