import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.departments.contracts import DepartmentToolRequest
from app.departments.finance.enums import BudgetStatus, FinancialTransactionStatus, FinancialTransactionType
from app.departments.finance.tools import FinanceBusinessDecisionError, FinanceToolService


def budget(amount: str = "100.00"):
    allocated = Decimal(amount)
    return SimpleNamespace(
        id=uuid4(), name="IT capital", currency="USD", status=BudgetStatus.ACTIVE,
        period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        allocated_amount=allocated, reserved_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"), spent_amount=Decimal("0.00"),
        available_amount=allocated,
    )


def request(operation: str, arguments: dict) -> DepartmentToolRequest:
    return DepartmentToolRequest(
        tool_name="finance", operation=operation, arguments=arguments,
        reason="Perform deterministic Finance operation", idempotency_key="workflow-key",
        expected_result_type="finance_tool_result",
    )


def service(record, *, approved_by=None, execution_confirmed=False):
    budgets, requests, transactions = AsyncMock(), AsyncMock(), AsyncMock()
    budgets.get.return_value = record
    requests.get.return_value = None
    transactions.get_by_reference.return_value = None

    async def add(values):
        return SimpleNamespace(id=uuid4(), **values)

    transactions.add.side_effect = add
    tool = FinanceToolService(
        budgets, requests, transactions, request_id=uuid4(), user_id=uuid4(),
        approved_by_user_id=approved_by, execution_confirmed=execution_confirmed,
    )
    return tool, budgets, requests, transactions


def test_automatic_reservation_locks_and_updates_once() -> None:
    record = budget()
    tool, budgets, _, transactions = service(record)
    result = asyncio.run(tool.execute(request("reserve_budget", {
        "budget_id": str(record.id), "amount": "25.25", "currency": "USD",
        "idempotency_reference": "finance:req:reservation",
    })))
    assert result["status"] == "confirmed"
    assert record.reserved_amount == Decimal("25.25")
    budgets.get.assert_awaited_once_with(record.id, for_update=True)
    transactions.add.assert_awaited_once()


def test_duplicate_reservation_returns_existing_without_mutating_budget() -> None:
    record = budget()
    tool, _, _, transactions = service(record)
    transactions.get_by_reference.return_value = SimpleNamespace(
        reference="finance:req:reservation", transaction_type=FinancialTransactionType.RESERVATION,
        status=FinancialTransactionStatus.CONFIRMED, amount=Decimal("25.00"), currency="USD",
    )
    result = asyncio.run(tool.execute(request("reserve_budget", {
        "budget_id": str(record.id), "amount": "25.00", "currency": "USD",
        "idempotency_reference": "finance:req:reservation",
    })))
    assert result["duplicate"] is True
    assert record.reserved_amount == Decimal("0.00")
    transactions.add.assert_not_awaited()


def test_two_reservations_cannot_overspend_locked_balance() -> None:
    record = budget("50.00")
    tool, _, _, _ = service(record)
    asyncio.run(tool.execute(request("reserve_budget", {
        "budget_id": str(record.id), "amount": "40.00", "currency": "USD",
        "idempotency_reference": "first",
    })))
    record.available_amount = record.allocated_amount - record.reserved_amount
    with pytest.raises(FinanceBusinessDecisionError, match="insufficient"):
        asyncio.run(tool.execute(request("reserve_budget", {
            "budget_id": str(record.id), "amount": "20.00", "currency": "USD",
            "idempotency_reference": "second",
        })))


def test_confirmed_commitment_requires_independent_authorization() -> None:
    record = budget()
    tool, _, _, _ = service(record)
    with pytest.raises(FinanceBusinessDecisionError, match="authorization"):
        asyncio.run(tool.execute(request("record_financial_transaction", {
            "budget_id": str(record.id), "transaction_type": "commitment",
            "amount": "10.00", "currency": "USD", "memo": "Approved item",
            "idempotency_reference": "commitment-one",
        })))


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"status": BudgetStatus.FROZEN}, "not active"),
        ({"period_end": date(2025, 12, 31)}, "period"),
        ({"currency": "EUR"}, "currency"),
    ],
)
def test_inactive_expired_and_currency_mismatch_are_business_rejections(change, message) -> None:
    record = budget()
    for key, value in change.items():
        setattr(record, key, value)
    tool, _, _, _ = service(record)
    with pytest.raises(FinanceBusinessDecisionError, match=message):
        asyncio.run(tool.execute(request("validate_budget_availability", {
            "budget_id": str(record.id), "amount": "10.00", "currency": "USD",
        })))


def test_release_reduces_reserved_total_and_is_confirmed_once() -> None:
    record = budget()
    record.reserved_amount = Decimal("20.00")
    tool, _, requests, transactions = service(record, approved_by=uuid4())
    original = SimpleNamespace(
        id=uuid4(), budget_id=record.id, reference="reservation-one",
        transaction_type=FinancialTransactionType.RESERVATION,
        status=FinancialTransactionStatus.CONFIRMED, amount=Decimal("20.00"), currency="USD",
    )
    transactions.get_by_reference.side_effect = [None, original]
    result = asyncio.run(tool.execute(request("release_budget_reservation", {
        "budget_id": str(record.id), "amount": "20.00", "currency": "USD",
        "reservation_reference": "reservation-one", "idempotency_reference": "release-one",
    })))
    assert result["transaction_type"] == "release"
    assert record.reserved_amount == Decimal("0.00")
    requests.get.assert_awaited_once()


def test_authorized_commitment_moves_reserved_total() -> None:
    record = budget()
    record.reserved_amount = Decimal("30.00")
    tool, _, _, _ = service(record, approved_by=uuid4())
    asyncio.run(tool.execute(request("record_financial_transaction", {
        "budget_id": str(record.id), "transaction_type": "commitment",
        "amount": "20.00", "currency": "USD", "memo": "Approved purchase commitment",
        "idempotency_reference": "commitment-approved",
    })))
    assert record.reserved_amount == Decimal("10.00")
    assert record.committed_amount == Decimal("20.00")
