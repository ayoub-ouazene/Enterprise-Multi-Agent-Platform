import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.repository import WorkflowEventRepository


def append_event(repository, request_id):
    return asyncio.run(
        repository.append(
            request_id=request_id,
            event_type=WorkflowEventType.REQUEST_CREATED,
            stage="request_received",
            title="Request created",
            message="The request has been created.",
            actor_type=WorkflowEventActorType.USER,
            actor_user_id=uuid4(),
            department_id=None,
            visibility=WorkflowEventVisibility.REQUESTER,
            event_data={},
        )
    )


def test_append_locks_tenant_request_and_assigns_next_sequence() -> None:
    company_id = uuid4()
    request_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [request_id, 4]
    repository = WorkflowEventRepository(session, company_id)

    event = append_event(repository, request_id)

    assert event is not None
    assert event.company_id == company_id
    assert event.request_id == request_id
    assert event.sequence_number == 5
    lock_statement = session.scalar.await_args_list[0].args[0]
    assert lock_statement._for_update_arg is not None
    assert company_id in set(lock_statement.compile().params.values())
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_first_event_sequence_is_one_for_each_request() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    request_one = uuid4()
    request_two = uuid4()
    session.scalar.side_effect = [request_one, 0, request_two, 0]
    repository = WorkflowEventRepository(session, company_id)

    first = append_event(repository, request_one)
    second = append_event(repository, request_two)

    assert first is not None and first.sequence_number == 1
    assert second is not None and second.sequence_number == 1


def test_cross_company_request_cannot_receive_event() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = WorkflowEventRepository(session, uuid4())

    event = append_event(repository, uuid4())

    assert event is None
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


def test_timeline_query_is_scoped_filtered_and_ordered() -> None:
    company_id = uuid4()
    request_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result
    repository = WorkflowEventRepository(session, company_id)

    result = asyncio.run(
        repository.list_for_request(
            request_id,
            visibilities=frozenset({WorkflowEventVisibility.REQUESTER}),
            limit=25,
            offset=2,
        )
    )

    assert result == []
    statement = session.scalars.await_args.args[0]
    compiled = statement.compile()
    compiled_values = list(compiled.params.values())
    assert company_id in compiled_values
    assert request_id in compiled_values
    assert "sequence_number ASC" in str(statement)


def test_repository_exposes_no_normal_update_or_delete_operation() -> None:
    assert not hasattr(WorkflowEventRepository, "update")
    assert not hasattr(WorkflowEventRepository, "delete")
