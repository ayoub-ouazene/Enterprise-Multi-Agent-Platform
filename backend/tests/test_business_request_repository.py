import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import models as database_models
from app.requests.enums import RequestPriority, RequestStatus
from app.requests.repository import BusinessRequestRepository


def test_get_by_id_is_tenant_scoped_and_cross_company_is_not_found() -> None:
    company_id = uuid4()
    request_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = BusinessRequestRepository(session, company_id)

    result = asyncio.run(repository.get_by_id(request_id))

    assert result is None
    statement = session.scalar.await_args.args[0]
    compiled_values = set(statement.compile().params.values())
    assert company_id in compiled_values
    assert request_id in compiled_values


def test_list_applies_employee_visibility_inside_query() -> None:
    company_id = uuid4()
    requester_user_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result
    repository = BusinessRequestRepository(session, company_id)

    result = asyncio.run(repository.list(requester_user_id=requester_user_id))

    assert result == []
    statement = session.scalars.await_args.args[0]
    compiled_values = set(statement.compile().params.values())
    assert company_id in compiled_values
    assert requester_user_id in compiled_values


def test_repository_create_assigns_tenant_and_never_commits() -> None:
    company_id = uuid4()
    requester_user_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    repository = BusinessRequestRepository(session, company_id)

    created = asyncio.run(
        repository.create(
            requester_user_id=requester_user_id,
            requester_employee_id=None,
            request_type="software_access",
            title="Access request",
            summary="Access is required.",
            priority=RequestPriority.NORMAL,
            workflow_state={},
            custom_data={},
        )
    )

    assert created.company_id == company_id
    assert created.requester_user_id == requester_user_id
    assert created.status == RequestStatus.CREATED
    assert created.owner_department_id is None
    assert created.active_department_id is None
    assert created.current_stage == "request_received"
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
    assert database_models.BusinessRequest is type(created)
