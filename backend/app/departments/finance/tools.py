from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.departments.contracts import DepartmentToolRequest
from app.departments.finance.enums import (
    BudgetStatus,
    FinancialTransactionStatus,
    FinancialTransactionType,
    ReservationStatus,
)
from app.departments.finance.repository import (
    BudgetRepository,
    FinanceRequestRepository,
    FinancialTransactionRepository,
)
from app.departments.finance.schemas import normalize_currency


CENT = Decimal("0.01")


class FinanceBusinessDecisionError(ValueError):
    """Expected financial rejection that must not become a system failure."""


class FinanceOperationError(RuntimeError):
    """Invalid or unavailable controlled Finance operation."""


def money(value: Any) -> Decimal:
    if isinstance(value, float):
        raise FinanceOperationError("floating-point monetary values are prohibited")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise FinanceOperationError("invalid monetary amount") from None
    if not amount.is_finite() or amount <= 0 or amount != amount.quantize(CENT):
        raise FinanceOperationError("amount must be positive with at most two decimal places")
    if len(amount.as_tuple().digits) > 18:
        raise FinanceOperationError("amount exceeds supported precision")
    return amount


class BudgetReadArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_id: UUID


class BudgetAmountArguments(BudgetReadArguments):
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str
    idempotency_reference: str | None = Field(
        default=None,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )

    @field_validator("amount", mode="before")
    @classmethod
    def decimal_only(cls, value: Any) -> Decimal:
        return money(value)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return normalize_currency(value) or value


class ReleaseArguments(BudgetAmountArguments):
    reservation_reference: str = Field(min_length=1, max_length=128)
    idempotency_reference: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )


class TransactionArguments(BudgetAmountArguments):
    transaction_type: FinancialTransactionType
    memo: str = Field(min_length=1, max_length=1000)
    idempotency_reference: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
    )
    reversed_transaction_id: UUID | None = None


class FinanceToolService:
    """Allowlisted deterministic Finance tools; the workflow service owns commits."""

    def __init__(
        self,
        budgets: BudgetRepository,
        requests: FinanceRequestRepository,
        transactions: FinancialTransactionRepository,
        *,
        request_id: UUID,
        user_id: UUID,
        approved_by_user_id: UUID | None = None,
        execution_confirmed: bool = False,
    ) -> None:
        self.budgets = budgets
        self.requests = requests
        self.transactions = transactions
        self.request_id = request_id
        self.user_id = user_id
        self.approved_by_user_id = approved_by_user_id
        self.execution_confirmed = execution_confirmed

    async def execute(self, request: DepartmentToolRequest) -> dict[str, Any]:
        operation = request.operation
        if operation == "get_budget_status":
            arguments = BudgetReadArguments.model_validate(request.arguments)
            budget = await self._budget(arguments.budget_id, lock=False)
            return self._status(operation, budget)
        if operation == "validate_budget_availability":
            arguments = BudgetAmountArguments.model_validate(request.arguments)
            budget = await self._budget(arguments.budget_id, lock=False)
            self._validate_budget(budget, arguments.amount, arguments.currency)
            return {**self._status(operation, budget), "amount": str(arguments.amount),
                "budget_sufficient": budget.available_amount >= arguments.amount}
        if operation == "reserve_budget":
            return await self._reserve(BudgetAmountArguments.model_validate(request.arguments))
        if operation == "release_budget_reservation":
            return await self._release(ReleaseArguments.model_validate(request.arguments))
        if operation == "record_financial_transaction":
            return await self._record(TransactionArguments.model_validate(request.arguments))
        raise FinanceOperationError("Finance tool operation is not allowlisted")

    async def _budget(self, budget_id: UUID, *, lock: bool):
        budget = await self.budgets.get(budget_id, for_update=lock)
        if budget is None:
            raise FinanceBusinessDecisionError("Budget not found")
        return budget

    @staticmethod
    def _validate_budget(budget, amount: Decimal, currency: str) -> None:
        today = date.today()
        if budget.status != BudgetStatus.ACTIVE:
            raise FinanceBusinessDecisionError("Budget is not active")
        if not (budget.period_start <= today <= budget.period_end):
            raise FinanceBusinessDecisionError("Budget period is not active")
        if budget.currency != currency:
            raise FinanceBusinessDecisionError("Budget currency does not match")
        if amount > budget.available_amount:
            raise FinanceBusinessDecisionError("Budget is insufficient")

    @staticmethod
    def _status(operation: str, budget) -> dict[str, Any]:
        return {
            "operation": operation,
            "budget_reference": budget.name,
            "currency": budget.currency,
            "available_amount": str(budget.available_amount),
            "status": budget.status.value,
        }

    async def _existing(self, reference: str | None):
        return await self.transactions.get_by_reference(reference) if reference else None

    async def _reserve(self, arguments: BudgetAmountArguments) -> dict[str, Any]:
        if arguments.idempotency_reference is None:
            raise FinanceOperationError("reservation requires an idempotency reference")
        budget = await self._budget(arguments.budget_id, lock=True)
        existing = await self._existing(arguments.idempotency_reference)
        if existing is not None:
            return self._transaction_result("reserve_budget", existing, duplicate=True)
        self._validate_budget(budget, arguments.amount, arguments.currency)
        transaction = await self.transactions.add({
            "request_id": self.request_id,
            "budget_id": budget.id,
            "transaction_type": FinancialTransactionType.RESERVATION,
            "amount": arguments.amount,
            "currency": arguments.currency,
            "status": FinancialTransactionStatus.CONFIRMED,
            "description": "Authorized budget reservation",
            "reference": arguments.idempotency_reference,
            "created_by_user_id": self.user_id,
            "approved_by_user_id": None,
            "confirmed_at": datetime.now(UTC),
            "reversed_transaction_id": None,
            "custom_data": {},
        })
        budget.reserved_amount += arguments.amount
        finance_request = await self.requests.get(self.request_id, for_update=True)
        if finance_request is not None:
            finance_request.reservation_status = ReservationStatus.RESERVED
        return self._transaction_result("reserve_budget", transaction, duplicate=False)

    async def _release(self, arguments: ReleaseArguments) -> dict[str, Any]:
        budget = await self._budget(arguments.budget_id, lock=True)
        existing = await self._existing(arguments.idempotency_reference)
        if existing is not None:
            return self._transaction_result("release_budget_reservation", existing, duplicate=True)
        original = await self.transactions.get_by_reference(arguments.reservation_reference)
        if (
            original is None
            or original.budget_id != budget.id
            or original.transaction_type != FinancialTransactionType.RESERVATION
            or original.status != FinancialTransactionStatus.CONFIRMED
            or original.amount != arguments.amount
        ):
            raise FinanceBusinessDecisionError("Confirmed reservation was not found")
        if budget.currency != arguments.currency or budget.reserved_amount < arguments.amount:
            raise FinanceBusinessDecisionError("Reservation cannot be released")
        transaction = await self.transactions.add({
            "request_id": self.request_id,
            "budget_id": budget.id,
            "transaction_type": FinancialTransactionType.RELEASE,
            "amount": arguments.amount,
            "currency": arguments.currency,
            "status": FinancialTransactionStatus.CONFIRMED,
            "description": "Budget reservation released",
            "reference": arguments.idempotency_reference,
            "created_by_user_id": self.user_id,
            "approved_by_user_id": self.approved_by_user_id,
            "confirmed_at": datetime.now(UTC),
            "reversed_transaction_id": None,
            "custom_data": {"reservation_reference": arguments.reservation_reference},
        })
        budget.reserved_amount -= arguments.amount
        finance_request = await self.requests.get(self.request_id, for_update=True)
        if finance_request is not None:
            finance_request.reservation_status = ReservationStatus.RELEASED
        return self._transaction_result("release_budget_reservation", transaction, duplicate=False)

    async def _record(self, arguments: TransactionArguments) -> dict[str, Any]:
        if arguments.transaction_type in {
            FinancialTransactionType.RESERVATION,
            FinancialTransactionType.RELEASE,
        }:
            raise FinanceOperationError("reservation and release require their dedicated tools")
        if self.approved_by_user_id is None or self.approved_by_user_id == self.user_id:
            raise FinanceBusinessDecisionError("Independent authorization is required")
        budget = await self._budget(arguments.budget_id, lock=True)
        existing = await self._existing(arguments.idempotency_reference)
        if existing is not None:
            return self._transaction_result("record_financial_transaction", existing, duplicate=True)
        if budget.currency != arguments.currency:
            raise FinanceBusinessDecisionError("Budget currency does not match")
        original = None
        if arguments.transaction_type == FinancialTransactionType.REVERSAL:
            if arguments.reversed_transaction_id is None:
                raise FinanceOperationError("reversal requires an original transaction")
            original = await self.transactions.get(arguments.reversed_transaction_id)
            if original is None or original.budget_id != budget.id or original.status != FinancialTransactionStatus.CONFIRMED:
                raise FinanceBusinessDecisionError("Reversible transaction was not found")
            if original.amount != arguments.amount or original.currency != arguments.currency:
                raise FinanceBusinessDecisionError("Reversal does not match the original transaction")
            self._reverse_totals(budget, original.transaction_type, arguments.amount)
            original.status = FinancialTransactionStatus.REVERSED
        else:
            self._apply_confirmed_totals(budget, arguments)
        transaction = await self.transactions.add({
            "request_id": self.request_id,
            "budget_id": budget.id,
            "transaction_type": arguments.transaction_type,
            "amount": arguments.amount,
            "currency": arguments.currency,
            "status": FinancialTransactionStatus.CONFIRMED,
            "description": arguments.memo,
            "reference": arguments.idempotency_reference,
            "created_by_user_id": self.user_id,
            "approved_by_user_id": self.approved_by_user_id,
            "confirmed_at": datetime.now(UTC),
            "reversed_transaction_id": original.id if original else None,
            "custom_data": {},
        })
        return self._transaction_result("record_financial_transaction", transaction, duplicate=False)

    def _apply_confirmed_totals(self, budget, arguments: TransactionArguments) -> None:
        amount = arguments.amount
        if arguments.transaction_type == FinancialTransactionType.COMMITMENT:
            if budget.reserved_amount >= amount:
                budget.reserved_amount -= amount
            elif amount > budget.available_amount:
                raise FinanceBusinessDecisionError("Budget is insufficient")
            budget.committed_amount += amount
        elif arguments.transaction_type == FinancialTransactionType.EXPENSE:
            if not self.execution_confirmed:
                raise FinanceBusinessDecisionError("Confirmed execution evidence is required")
            if budget.committed_amount >= amount:
                budget.committed_amount -= amount
            elif amount > budget.available_amount:
                raise FinanceBusinessDecisionError("Budget is insufficient")
            budget.spent_amount += amount
        elif arguments.transaction_type == FinancialTransactionType.ADJUSTMENT:
            budget.allocated_amount += amount
        else:
            raise FinanceOperationError("unsupported confirmed transaction type")

    @staticmethod
    def _reverse_totals(budget, transaction_type: FinancialTransactionType, amount: Decimal) -> None:
        field = {
            FinancialTransactionType.RESERVATION: "reserved_amount",
            FinancialTransactionType.COMMITMENT: "committed_amount",
            FinancialTransactionType.EXPENSE: "spent_amount",
            FinancialTransactionType.ADJUSTMENT: "allocated_amount",
        }.get(transaction_type)
        if field is None or getattr(budget, field) < amount:
            raise FinanceBusinessDecisionError("Transaction cannot be reversed")
        setattr(budget, field, getattr(budget, field) - amount)

    @staticmethod
    def _transaction_result(operation: str, transaction, *, duplicate: bool) -> dict[str, Any]:
        return {
            "operation": operation,
            "transaction_reference": transaction.reference,
            "transaction_type": transaction.transaction_type.value,
            "status": transaction.status.value,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "duplicate": duplicate,
        }
