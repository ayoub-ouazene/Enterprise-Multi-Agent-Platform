import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.failures.enums import FailureSource, FailureType
from app.failures.repository import FailureLogRepository


def create_failure(repository, request_id=None, department_id=None):
    return asyncio.run(
        repository.create(
            request_id=request_id,
            department_id=department_id,
            failure_type=FailureType.DATABASE_FAILURE,
            failure_source=FailureSource.REPOSITORY,
            failed_operation="read_inventory",
            internal_message="sanitized",
            safe_message="Safe message",
            error_code="DB_READ",
            technical_data={},
            alternative_attempted=True,
            alternative_description="Cache checked",
            is_terminal=False,
        )
    )


def test_failure_creation_validates_tenant_references_and_never_commits() -> None:
    request_id, department_id = uuid4(), uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [request_id, department_id]
    repository = FailureLogRepository(session, uuid4())
    failure = create_failure(repository, request_id, department_id)
    assert failure is not None
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_cross_company_failure_reference_is_rejected() -> None:
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = FailureLogRepository(session, uuid4())
    assert create_failure(repository, uuid4()) is None
    session.add.assert_not_called()


def test_failure_repository_has_only_controlled_resolution_update() -> None:
    assert hasattr(FailureLogRepository, "resolve")
    assert not hasattr(FailureLogRepository, "update")
    assert not hasattr(FailureLogRepository, "delete")
