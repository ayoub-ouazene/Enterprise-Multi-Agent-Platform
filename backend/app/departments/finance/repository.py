from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.finance.enums import BudgetStatus
from app.departments.finance.models import Budget, FinanceRequest, FinancialTransaction


class BudgetRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, budget_id: UUID, *, for_update: bool = False) -> Budget | None:
        statement = select(Budget).where(
            Budget.id == budget_id,
            Budget.company_id == self.company_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        active_on: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Budget]:
        statement = select(Budget).where(Budget.company_id == self.company_id)
        if department_id is not None:
            statement = statement.where(Budget.department_id == department_id)
        if active_on is not None:
            statement = statement.where(
                Budget.status == BudgetStatus.ACTIVE,
                Budget.period_start <= active_on,
                Budget.period_end >= active_on,
            )
        result = await self.session.scalars(
            statement.order_by(Budget.period_end.desc(), Budget.name).limit(limit).offset(offset)
        )
        return list(result.all())

    async def find_current(
        self,
        *,
        department_id: UUID | None,
        currency: str | None,
        on_date: date,
    ) -> list[Budget]:
        statement = select(Budget).where(
            Budget.company_id == self.company_id,
            Budget.status == BudgetStatus.ACTIVE,
            Budget.period_start <= on_date,
            Budget.period_end >= on_date,
        )
        if department_id is None:
            statement = statement.where(Budget.department_id.is_(None))
        else:
            statement = statement.where(Budget.department_id == department_id)
        if currency is not None:
            statement = statement.where(Budget.currency == currency)
        result = await self.session.scalars(statement.order_by(Budget.name))
        return list(result.all())


class FinanceRequestRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, request_id: UUID, *, for_update: bool = False) -> FinanceRequest | None:
        statement = select(FinanceRequest).where(
            FinanceRequest.request_id == request_id,
            FinanceRequest.company_id == self.company_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert(self, request_id: UUID, values: dict[str, object]) -> FinanceRequest:
        record = await self.get(request_id, for_update=True)
        if record is None:
            record = FinanceRequest(
                request_id=request_id,
                company_id=self.company_id,
                **values,
            )
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record


class FinancialTransactionRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, transaction_id: UUID) -> FinancialTransaction | None:
        return await self.session.scalar(
            select(FinancialTransaction).where(
                FinancialTransaction.id == transaction_id,
                FinancialTransaction.company_id == self.company_id,
            )
        )

    async def get_by_reference(self, reference: str) -> FinancialTransaction | None:
        return await self.session.scalar(
            select(FinancialTransaction).where(
                FinancialTransaction.company_id == self.company_id,
                FinancialTransaction.reference == reference,
            )
        )

    async def list(
        self,
        *,
        budget_id: UUID | None = None,
        request_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FinancialTransaction]:
        statement = select(FinancialTransaction).where(
            FinancialTransaction.company_id == self.company_id
        )
        if budget_id is not None:
            statement = statement.where(FinancialTransaction.budget_id == budget_id)
        if request_id is not None:
            statement = statement.where(FinancialTransaction.request_id == request_id)
        result = await self.session.scalars(
            statement.order_by(FinancialTransaction.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.all())

    async def add(self, values: dict[str, object]) -> FinancialTransaction:
        transaction = FinancialTransaction(company_id=self.company_id, **values)
        self.session.add(transaction)
        await self.session.flush()
        return transaction
