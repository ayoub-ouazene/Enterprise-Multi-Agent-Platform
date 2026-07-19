import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.finance.enums import BudgetStatus, FinanceModelRole
from app.departments.finance.service import FinanceService
from app.rag.enums import KnowledgeDepartmentScope, KnowledgeDocumentType
from app.rag.exceptions import KnowledgeProviderError
from tests.test_finance_contracts import valid_finance_result


def settings() -> Settings:
    return Settings(
        _env_file=None, debug=False,
        database_url="postgresql+asyncpg://u:p@pooled.example/db",
        alembic_database_url="postgresql+asyncpg://u:p@direct.example/db",
    )


def budget():
    return SimpleNamespace(
        id=uuid4(), department_id=None, name="Company operations", currency="USD",
        status=BudgetStatus.ACTIVE, period_start=date(2026, 1, 1),
        period_end=date(2026, 12, 31), allocated_amount=Decimal("1000.00"),
        reserved_amount=Decimal("100.00"), committed_amount=Decimal("200.00"),
        spent_amount=Decimal("300.00"), available_amount=Decimal("400.00"),
        approval_threshold=Decimal("500.00"),
    )


def context(current, **changes) -> DepartmentExecutionContext:
    values = dict(
        request_id=uuid4(), company_id=current.company_id,
        requester_user_id=current.user_id, requester_actor_type=current.actor_type,
        owner_department_type=DepartmentType.FINANCE,
        active_department_type=DepartmentType.FINANCE,
        request_type="budget_validation", request_summary="Can we spend 100 USD?",
        current_stage="finance_analysis",
        relevant_custom_data={"requested_amount": "100.00", "currency": "USD"},
    )
    values.update(changes)
    return DepartmentExecutionContext(**values)


def service_setup():
    current = AuthenticatedUser(uuid4(), uuid4(), "finance@example.com", ActorType.COMPANY)
    session, retrieval, llm = AsyncMock(), AsyncMock(), AsyncMock()
    budgets, requests, transactions = AsyncMock(), AsyncMock(), AsyncMock()
    record = budget()
    budgets.get.return_value = None
    budgets.find_current.return_value = [record]
    transactions.list.return_value = []
    evidence_id = uuid4()
    retrieval.search_trusted.return_value = [SimpleNamespace(
        document_id=evidence_id, title="Finance policy",
        document_type=KnowledgeDocumentType.POLICY, version=1, chunk_index=0,
        effective_date=None, chunk_text="Budget checks are required.",
    )]
    llm.generate.return_value = valid_finance_result(
        decision="validated", requested_amount="100.00", currency="USD",
        available_budget="400.00", budget_sufficient=True, policy_compliant=True,
    )
    service = FinanceService(
        session, current, settings(), retrieval, llm_client=llm,
        budget_repository=budgets, finance_request_repository=requests,
        transaction_repository=transactions,
    )
    return service, current, session, retrieval, llm, budgets, requests, record


def test_service_uses_finance_shared_rag_and_deterministic_budget() -> None:
    service, current, session, retrieval, llm, _, _, _ = service_setup()
    result = asyncio.run(service.execute(context(current)))
    query = retrieval.search_trusted.await_args.args[0]
    assert query.departments == [KnowledgeDepartmentScope.FINANCE, KnowledgeDepartmentScope.SHARED]
    assert result.department_type == DepartmentType.FINANCE
    assert llm.generate.await_args.kwargs["role"] == FinanceModelRole.FAST
    assert session.rollback.await_count == 2


def test_model_cannot_invent_available_balance() -> None:
    service, current, _, _, llm, _, _, _ = service_setup()
    llm.generate.return_value = valid_finance_result(
        requested_amount="100.00", currency="USD", available_budget="999.00",
        budget_sufficient=True,
    )
    with pytest.raises(ValueError, match="deterministic"):
        asyncio.run(service.execute(context(current)))


def test_finance_extension_is_persisted_without_commit() -> None:
    service, _, session, _, _, _, requests, record = service_setup()
    result = valid_finance_result(
        requested_amount="100.00", currency="USD", available_budget="400.00",
        budget_sufficient=True, policy_compliant=True,
        state_updates={"budget_id": str(record.id), "business_reason": "Operations"},
    )
    asyncio.run(service.persist_result(uuid4(), result))
    requests.upsert.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_pinecone_failure_is_sanitized_and_skips_groq() -> None:
    service, current, _, retrieval, llm, _, _, _ = service_setup()
    retrieval.search_trusted.side_effect = KnowledgeProviderError(
        "Company knowledge is temporarily unavailable"
    )
    with pytest.raises(KnowledgeProviderError, match="temporarily unavailable"):
        asyncio.run(service.execute(context(current)))
    llm.generate.assert_not_awaited()
