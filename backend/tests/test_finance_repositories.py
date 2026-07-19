import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from app.departments.finance.repository import (
    BudgetRepository,
    FinanceRequestRepository,
    FinancialTransactionRepository,
)


def test_budget_lookup_is_company_scoped_and_supports_row_lock() -> None:
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None
    company_id = uuid4()
    result = asyncio.run(BudgetRepository(session, company_id).get(uuid4(), for_update=True))
    statement = session.scalar.await_args.args[0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert result is None
    assert "budgets.company_id" in compiled
    assert "for update" in compiled


def test_cross_company_finance_records_behave_as_not_found() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    assert asyncio.run(FinanceRequestRepository(session, uuid4()).get(uuid4())) is None
    assert asyncio.run(FinancialTransactionRepository(session, uuid4()).get(uuid4())) is None


def test_repositories_flush_but_never_commit() -> None:
    session = AsyncMock()
    session.add = Mock()
    session.scalar.return_value = None
    repo = FinanceRequestRepository(session, uuid4())
    values = {
        "category": "budget_inquiry", "business_reason": "Plan operations",
        "decision": "answer", "decision_reason": "Validated", "custom_data": {},
    }
    asyncio.run(repo.upsert(uuid4(), values))
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
