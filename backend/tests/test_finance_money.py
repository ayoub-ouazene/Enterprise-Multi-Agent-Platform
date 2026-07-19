from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import Numeric

from app.departments.finance.enums import BudgetStatus, BudgetType
from app.departments.finance.models import Budget, FinancialTransaction
from app.departments.finance.schemas import normalize_currency
from app.departments.finance.tools import FinanceOperationError, money


def budget() -> Budget:
    return Budget(
        company_id=uuid4(), name="Operations", budget_type=BudgetType.OPERATIONAL,
        currency="USD", period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        allocated_amount=Decimal("1000.00"), reserved_amount=Decimal("100.10"),
        committed_amount=Decimal("200.20"), spent_amount=Decimal("300.30"),
        status=BudgetStatus.ACTIVE,
    )


def test_available_amount_uses_exact_decimal_arithmetic() -> None:
    assert budget().available_amount == Decimal("399.40")
    assert isinstance(budget().available_amount, Decimal)


def test_money_columns_are_fixed_precision_not_float() -> None:
    for model, columns in (
        (Budget, ("allocated_amount", "reserved_amount", "committed_amount", "spent_amount")),
        (FinancialTransaction, ("amount",)),
    ):
        for name in columns:
            column_type = model.__table__.c[name].type
            assert isinstance(column_type, Numeric)
            assert (column_type.precision, column_type.scale) == (18, 2)


def test_float_and_excess_precision_are_rejected() -> None:
    with pytest.raises(FinanceOperationError, match="floating-point"):
        money(1.25)
    with pytest.raises(FinanceOperationError, match="two decimal"):
        money("1.001")


def test_currency_is_normalized_and_validated() -> None:
    assert normalize_currency(" usd ") == "USD"
    with pytest.raises(ValueError, match="three-letter"):
        normalize_currency("US")
