import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.database import models as database_models
from app.departments.procurement.repository import (
    ProcurementRequestRepository,
    SupplierCandidateRepository,
)


_ = database_models


def test_procurement_request_get_is_company_scoped_and_lockable() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    repository = ProcurementRequestRepository(session, uuid4())
    assert asyncio.run(repository.get(uuid4(), for_update=True)) is None
    statement = session.scalar.await_args.args[0]
    assert "company_id" in str(statement)
    assert "FOR UPDATE" in str(statement)


def test_candidate_get_cross_company_behaves_as_not_found() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    repository = SupplierCandidateRepository(session, uuid4())
    assert asyncio.run(repository.get(uuid4())) is None
    assert "company_id" in str(session.scalar.await_args.args[0])


def test_candidate_list_has_deterministic_order_and_request_scope() -> None:
    session = AsyncMock()
    session.scalars.return_value = SimpleNamespace(all=lambda: [])
    repository = SupplierCandidateRepository(session, uuid4())
    assert asyncio.run(repository.list_for_request(uuid4())) == []
    statement = str(session.scalars.await_args.args[0])
    assert "request_id" in statement
    assert "ORDER BY" in statement
