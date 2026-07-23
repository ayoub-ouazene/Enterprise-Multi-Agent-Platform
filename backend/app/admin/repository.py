"""Admin repositories — extend existing ones with optimistic locking & list ops."""
from datetime import date
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Supplier
from app.core.enums import EmploymentStatus
from app.departments.finance.models import Budget
from app.departments.hr.models import CompanyHoliday, DepartmentStaffingRule, LeaveBalance
from app.departments.it.models import Asset, SoftwareCatalog
from app.employees.models import Employee


# ---------------------------------------------------------------------------
# Supplier (new table)
# ---------------------------------------------------------------------------

class SupplierRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, supplier_id: UUID) -> Supplier | None:
        return await self.session.scalar(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.company_id == self.company_id,
            )
        )

    async def get_by_name(self, name: str) -> Supplier | None:
        return await self.session.scalar(
            select(Supplier).where(
                Supplier.company_id == self.company_id,
                func.lower(Supplier.name) == name.strip().lower(),
            )
        )

    async def list(
        self,
        *,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Supplier]:
        statement = select(Supplier).where(Supplier.company_id == self.company_id)
        if is_active is not None:
            statement = statement.where(Supplier.is_active.is_(is_active))
        result = await self.session.scalars(
            statement.order_by(Supplier.name).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> Supplier:
        supplier = Supplier(company_id=self.company_id, **values)
        self.session.add(supplier)
        await self.session.flush()
        return supplier

    async def update(
        self,
        supplier_id: UUID,
        values: dict[str, object],
    ) -> Supplier | None:
        if not values:
            return await self.get(supplier_id)
        statement = (
            update(Supplier)
            .where(
                Supplier.id == supplier_id,
                Supplier.company_id == self.company_id,
            )
            .values(**values)
            .returning(Supplier)
        )
        return await self.session.scalar(statement)

    async def delete(self, supplier_id: UUID) -> bool:
        result = await self.session.execute(
            update(Supplier)
            .where(
                Supplier.id == supplier_id,
                Supplier.company_id == self.company_id,
            )
            .values(is_active=False)
        )
        return bool(result.rowcount)

    async def hard_delete(self, supplier_id: UUID) -> bool:
        result = await self.session.execute(
            update(Supplier)
            .where(Supplier.id == supplier_id, Supplier.company_id == self.company_id)
            .values(is_active=False)
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Employee (admin CRUD)
# ---------------------------------------------------------------------------

class EmployeeAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, employee_id: UUID) -> Employee | None:
        return await self.session.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == self.company_id,
            )
        )

    async def get_by_code(self, employee_code: str) -> Employee | None:
        return await self.session.scalar(
            select(Employee).where(
                Employee.company_id == self.company_id,
                Employee.employee_code == employee_code,
            )
        )

    async def get_by_email(self, email: str) -> Employee | None:
        from app.users.models import User

        return await self.session.scalar(
            select(Employee)
            .join(User, Employee.user_id == User.id)
            .where(
                Employee.company_id == self.company_id,
                func.lower(User.email) == email.strip().lower(),
            )
        )

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        status: EmploymentStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Employee]:
        statement = select(Employee).where(Employee.company_id == self.company_id)
        if department_id is not None:
            statement = statement.where(Employee.department_id == department_id)
        if status is not None:
            statement = statement.where(Employee.employment_status == status)
        result = await self.session.scalars(
            statement.order_by(Employee.employee_code).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> Employee:
        employee = Employee(company_id=self.company_id, **values)
        self.session.add(employee)
        await self.session.flush()
        return employee

    async def update(
        self,
        employee_id: UUID,
        values: dict[str, object],
    ) -> Employee | None:
        if not values:
            return await self.get(employee_id)
        statement = (
            update(Employee)
            .where(
                Employee.id == employee_id,
                Employee.company_id == self.company_id,
            )
            .values(**values)
            .returning(Employee)
        )
        return await self.session.scalar(statement)

    async def soft_delete(self, employee_id: UUID) -> bool:
        result = await self.session.execute(
            update(Employee)
            .where(
                Employee.id == employee_id,
                Employee.company_id == self.company_id,
            )
            .values(employment_status=EmploymentStatus.TERMINATED)
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Asset (admin CRUD with optimistic locking)
# ---------------------------------------------------------------------------

class AssetAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, asset_id: UUID) -> Asset | None:
        return await self.session.scalar(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        asset_type: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Asset]:
        statement = select(Asset).where(Asset.company_id == self.company_id)
        if asset_type is not None:
            statement = statement.where(
                func.lower(Asset.asset_type) == asset_type.strip().lower()
            )
        if status is not None:
            statement = statement.where(Asset.status == status)
        result = await self.session.scalars(
            statement.order_by(Asset.asset_code).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> Asset:
        asset = Asset(company_id=self.company_id, version=1, **values)
        self.session.add(asset)
        await self.session.flush()
        return asset

    async def update(
        self,
        asset_id: UUID,
        values: dict[str, object],
        expected_version: int,
    ) -> Asset | None:
        if not values:
            return await self.get(asset_id)
        values["version"] = expected_version + 1
        statement = (
            update(Asset)
            .where(
                Asset.id == asset_id,
                Asset.company_id == self.company_id,
                Asset.version == expected_version,
            )
            .values(**values)
            .returning(Asset)
        )
        return await self.session.scalar(statement)

    async def soft_delete(self, asset_id: UUID) -> bool:
        result = await self.session.execute(
            update(Asset)
            .where(Asset.id == asset_id, Asset.company_id == self.company_id)
            .values(status="retired")
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Software Catalog (admin CRUD with optimistic locking)
# ---------------------------------------------------------------------------

class SoftwareCatalogAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, software_id: UUID) -> SoftwareCatalog | None:
        return await self.session.scalar(
            select(SoftwareCatalog).where(
                SoftwareCatalog.id == software_id,
                SoftwareCatalog.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SoftwareCatalog]:
        statement = select(SoftwareCatalog).where(
            SoftwareCatalog.company_id == self.company_id
        )
        if is_active is not None:
            statement = statement.where(SoftwareCatalog.is_active.is_(is_active))
        result = await self.session.scalars(
            statement.order_by(SoftwareCatalog.name).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> SoftwareCatalog:
        software = SoftwareCatalog(company_id=self.company_id, version=1, **values)
        self.session.add(software)
        await self.session.flush()
        return software

    async def update(
        self,
        software_id: UUID,
        values: dict[str, object],
        expected_version: int,
    ) -> SoftwareCatalog | None:
        if not values:
            return await self.get(software_id)
        values["version"] = expected_version + 1
        statement = (
            update(SoftwareCatalog)
            .where(
                SoftwareCatalog.id == software_id,
                SoftwareCatalog.company_id == self.company_id,
                SoftwareCatalog.version == expected_version,
            )
            .values(**values)
            .returning(SoftwareCatalog)
        )
        return await self.session.scalar(statement)

    async def soft_delete(self, software_id: UUID) -> bool:
        result = await self.session.execute(
            update(SoftwareCatalog)
            .where(
                SoftwareCatalog.id == software_id,
                SoftwareCatalog.company_id == self.company_id,
            )
            .values(is_active=False)
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Budget (admin CRUD with optimistic locking)
# ---------------------------------------------------------------------------

class BudgetAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, budget_id: UUID) -> Budget | None:
        return await self.session.scalar(
            select(Budget).where(
                Budget.id == budget_id,
                Budget.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Budget]:
        statement = select(Budget).where(Budget.company_id == self.company_id)
        if department_id is not None:
            statement = statement.where(Budget.department_id == department_id)
        if status is not None:
            statement = statement.where(Budget.status == status)
        result = await self.session.scalars(
            statement.order_by(Budget.period_end.desc(), Budget.name).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> Budget:
        budget = Budget(company_id=self.company_id, version=1, **values)
        self.session.add(budget)
        await self.session.flush()
        return budget

    async def update(
        self,
        budget_id: UUID,
        values: dict[str, object],
        expected_version: int,
    ) -> Budget | None:
        if not values:
            return await self.get(budget_id)
        values["version"] = expected_version + 1
        statement = (
            update(Budget)
            .where(
                Budget.id == budget_id,
                Budget.company_id == self.company_id,
                Budget.version == expected_version,
            )
            .values(**values)
            .returning(Budget)
        )
        return await self.session.scalar(statement)

    async def soft_delete(self, budget_id: UUID) -> bool:
        result = await self.session.execute(
            update(Budget)
            .where(Budget.id == budget_id, Budget.company_id == self.company_id)
            .values(status="closed")
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Leave Balance (admin CRUD)
# ---------------------------------------------------------------------------

class LeaveBalanceAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, balance_id: UUID) -> LeaveBalance | None:
        return await self.session.scalar(
            select(LeaveBalance).where(
                LeaveBalance.id == balance_id,
                LeaveBalance.company_id == self.company_id,
            )
        )

    async def list_for_employee(self, employee_id: UUID) -> list[LeaveBalance]:
        result = await self.session.scalars(
            select(LeaveBalance)
            .where(
                LeaveBalance.company_id == self.company_id,
                LeaveBalance.employee_id == employee_id,
            )
            .order_by(LeaveBalance.year.desc(), LeaveBalance.leave_type)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> LeaveBalance:
        balance = LeaveBalance(company_id=self.company_id, **values)
        self.session.add(balance)
        await self.session.flush()
        return balance

    async def update(
        self,
        balance_id: UUID,
        values: dict[str, object],
    ) -> LeaveBalance | None:
        if not values:
            return await self.get(balance_id)
        statement = (
            update(LeaveBalance)
            .where(
                LeaveBalance.id == balance_id,
                LeaveBalance.company_id == self.company_id,
            )
            .values(**values)
            .returning(LeaveBalance)
        )
        return await self.session.scalar(statement)

    async def delete(self, balance_id: UUID) -> bool:
        result = await self.session.execute(
            update(LeaveBalance)
            .where(
                LeaveBalance.id == balance_id,
                LeaveBalance.company_id == self.company_id,
            )
            # Soft-delete by zeroing; but for balances we just hard-delete
            # since they have no children except request-scoped usage.
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Company Holiday (admin CRUD)
# ---------------------------------------------------------------------------

class CompanyHolidayAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, holiday_id: UUID) -> CompanyHoliday | None:
        return await self.session.scalar(
            select(CompanyHoliday).where(
                CompanyHoliday.id == holiday_id,
                CompanyHoliday.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        year: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CompanyHoliday]:
        statement = select(CompanyHoliday).where(
            CompanyHoliday.company_id == self.company_id
        )
        if year is not None:
            statement = statement.where(
                func.extract("year", CompanyHoliday.holiday_date) == year
            )
        result = await self.session.scalars(
            statement.order_by(CompanyHoliday.holiday_date).limit(limit).offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> CompanyHoliday:
        holiday = CompanyHoliday(company_id=self.company_id, **values)
        self.session.add(holiday)
        await self.session.flush()
        return holiday

    async def update(
        self,
        holiday_id: UUID,
        values: dict[str, object],
    ) -> CompanyHoliday | None:
        if not values:
            return await self.get(holiday_id)
        statement = (
            update(CompanyHoliday)
            .where(
                CompanyHoliday.id == holiday_id,
                CompanyHoliday.company_id == self.company_id,
            )
            .values(**values)
            .returning(CompanyHoliday)
        )
        return await self.session.scalar(statement)

    async def hard_delete(self, holiday_id: UUID) -> bool:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(CompanyHoliday).where(
                CompanyHoliday.id == holiday_id,
                CompanyHoliday.company_id == self.company_id,
            )
        )
        return bool(result.rowcount)


# ---------------------------------------------------------------------------
# Department Staffing Rule (admin CRUD)
# ---------------------------------------------------------------------------

class StaffingRuleAdminRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get(self, rule_id: UUID) -> DepartmentStaffingRule | None:
        return await self.session.scalar(
            select(DepartmentStaffingRule).where(
                DepartmentStaffingRule.id == rule_id,
                DepartmentStaffingRule.company_id == self.company_id,
            )
        )

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        is_active: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DepartmentStaffingRule]:
        statement = select(DepartmentStaffingRule).where(
            DepartmentStaffingRule.company_id == self.company_id
        )
        if department_id is not None:
            statement = statement.where(
                DepartmentStaffingRule.department_id == department_id
            )
        if is_active is not None:
            statement = statement.where(
                DepartmentStaffingRule.is_active.is_(is_active)
            )
        result = await self.session.scalars(
            statement.order_by(DepartmentStaffingRule.effective_from.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.all())

    async def create(self, values: dict[str, object]) -> DepartmentStaffingRule:
        rule = DepartmentStaffingRule(company_id=self.company_id, **values)
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def update(
        self,
        rule_id: UUID,
        values: dict[str, object],
    ) -> DepartmentStaffingRule | None:
        if not values:
            return await self.get(rule_id)
        statement = (
            update(DepartmentStaffingRule)
            .where(
                DepartmentStaffingRule.id == rule_id,
                DepartmentStaffingRule.company_id == self.company_id,
            )
            .values(**values)
            .returning(DepartmentStaffingRule)
        )
        return await self.session.scalar(statement)

    async def hard_delete(self, rule_id: UUID) -> bool:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(DepartmentStaffingRule).where(
                DepartmentStaffingRule.id == rule_id,
                DepartmentStaffingRule.company_id == self.company_id,
            )
        )
        return bool(result.rowcount)
