"""Admin service — business logic for company data management."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dependencies import _is_company
from app.admin.repository import (
    AssetAdminRepository,
    BudgetAdminRepository,
    CompanyHolidayAdminRepository,
    EmployeeAdminRepository,
    LeaveBalanceAdminRepository,
    SoftwareCatalogAdminRepository,
    StaffingRuleAdminRepository,
    SupplierRepository,
)
from app.admin.schemas import (
    AdminAssetCreate,
    AdminAssetUpdate,
    AdminBudgetCreate,
    AdminBudgetUpdate,
    AdminDepartmentUpdate,
    AdminEmployeeCreate,
    AdminEmployeeUpdate,
    AdminHolidayCreate,
    AdminHolidayUpdate,
    AdminLeaveBalanceCreate,
    AdminLeaveBalanceUpdate,
    AdminSoftwareCatalogCreate,
    AdminSoftwareCatalogUpdate,
    AdminStaffingRuleCreate,
    AdminStaffingRuleUpdate,
    AdminSupplierCreate,
    AdminSupplierUpdate,
)
from app.auth.context import AuthenticatedUser
from app.auth.passwords import hash_password
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    NotFoundError,
)
from app.departments.finance.models import Budget
from app.departments.repository import DepartmentRepository
from app.employees.models import Employee
from app.users.models import User


class AdminServiceError(Exception):
    pass


class OptimisticLockError(AdminServiceError):
    pass


class AdminEmployeeService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = EmployeeAdminRepository(session, company_id)

    async def list(
        self,
        *,
        department_id: UUID | None = None,
        status: EmploymentStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Employee]:
        return await self.repo.list(
            department_id=department_id, status=status, limit=limit, offset=offset
        )

    async def get(self, employee_id: UUID) -> Employee | None:
        return await self.repo.get(employee_id)

    async def create(
        self,
        payload: AdminEmployeeCreate,
        current_user: AuthenticatedUser,
    ) -> Employee:
        if await self.repo.get_by_code(payload.employee_code):
            raise ConflictError("Employee code already exists")

        # Resolve department if name/type provided
        department_id = payload.department_id

        # Create user account for employee
        password_hash = hash_password("TempPass123!") if _is_company(current_user) else None
        user = User(
            company_id=self.company_id,
            email=payload.email,
            password_hash=password_hash,
            actor_type=ActorType.EMPLOYEE,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()

        emp = await self.repo.create(
            {
                "user_id": user.id,
                "department_id": department_id,
                "employee_code": payload.employee_code,
                "job_title": payload.job_title,
                "hire_date": payload.hire_date,
                "manager_employee_id": payload.manager_employee_id,
                "employment_status": payload.employment_status,
                "custom_data": payload.custom_data,
            }
        )
        return emp

    async def update(
        self,
        employee_id: UUID,
        payload: AdminEmployeeUpdate,
    ) -> Employee:
        emp = await self.repo.get(employee_id)
        if emp is None:
            raise NotFoundError("Employee not found")
        values: dict[str, object] = {}
        for field in (
            "employee_code",
            "job_title",
            "department_id",
            "hire_date",
            "manager_employee_id",
            "employment_status",
            "custom_data",
        ):
            v = getattr(payload, field)
            if v is not None:
                values[field] = v
        updated = await self.repo.update(employee_id, values)
        if updated is None:
            raise NotFoundError("Employee not found")
        return updated

    async def soft_delete(self, employee_id: UUID) -> bool:
        emp = await self.repo.get(employee_id)
        if emp is None:
            raise NotFoundError("Employee not found")
        return await self.repo.soft_delete(employee_id)


class AdminDepartmentService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = DepartmentRepository(session, company_id)

    async def list(self) -> list:
        return await self.repo.list()

    async def get(self, department_id: UUID):
        dept = await self.repo.get_by_id(department_id)
        if dept is None:
            raise NotFoundError("Department not found")
        return dept

    async def update(
        self,
        department_id: UUID,
        payload: AdminDepartmentUpdate,
    ):
        dept = await self.repo.get_by_id(department_id)
        if dept is None:
            raise NotFoundError("Department not found")
        values: dict[str, object] = {}
        for field in ("name", "is_active", "custom_data"):
            v = getattr(payload, field)
            if v is not None:
                values[field] = v
        updated = await self.repo.update(department_id, values)
        if updated is None:
            raise NotFoundError("Department not found")
        return updated


class AdminAssetService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = AssetAdminRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, asset_id: UUID):
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        return asset

    async def create(self, payload: AdminAssetCreate):
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, asset_id: UUID, payload: AdminAssetUpdate):
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        values = payload.model_dump(exclude={"version"}, exclude_unset=True)
        updated = await self.repo.update(asset_id, values, payload.version)
        if updated is None:
            raise OptimisticLockError("Asset was modified by another user")
        return updated

    async def soft_delete(self, asset_id: UUID) -> bool:
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        return await self.repo.soft_delete(asset_id)


class AdminSoftwareCatalogService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = SoftwareCatalogAdminRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, software_id: UUID):
        s = await self.repo.get(software_id)
        if s is None:
            raise NotFoundError("Software catalog entry not found")
        return s

    async def create(self, payload: AdminSoftwareCatalogCreate):
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, software_id: UUID, payload: AdminSoftwareCatalogUpdate):
        s = await self.repo.get(software_id)
        if s is None:
            raise NotFoundError("Software catalog entry not found")
        values = payload.model_dump(exclude={"version"}, exclude_unset=True)
        updated = await self.repo.update(software_id, values, payload.version)
        if updated is None:
            raise OptimisticLockError("Software catalog entry was modified")
        return updated

    async def soft_delete(self, software_id: UUID) -> bool:
        s = await self.repo.get(software_id)
        if s is None:
            raise NotFoundError("Software catalog entry not found")
        return await self.repo.soft_delete(software_id)


class AdminBudgetService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = BudgetAdminRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, budget_id: UUID) -> Budget:
        b = await self.repo.get(budget_id)
        if b is None:
            raise NotFoundError("Budget not found")
        return b

    async def create(self, payload: AdminBudgetCreate) -> Budget:
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, budget_id: UUID, payload: AdminBudgetUpdate) -> Budget:
        budget = await self.repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Budget not found")

        values = payload.model_dump(exclude={"version"}, exclude_unset=True)

        # Guard: cannot reduce allocated below reserved + committed + spent
        if "allocated_amount" in values:
            new_allocated = Decimal(str(values["allocated_amount"]))
            total_used = (
                budget.reserved_amount
                + budget.committed_amount
                + budget.spent_amount
            )
            if new_allocated < total_used:
                raise BusinessValidationError(
                    "allocated_amount cannot be less than reserved + committed + spent"
                )
            values["allocated_amount"] = new_allocated

        updated = await self.repo.update(budget_id, values, payload.version)
        if updated is None:
            raise OptimisticLockError("Budget was modified by another user")
        return updated

    async def soft_delete(self, budget_id: UUID) -> bool:
        budget = await self.repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Budget not found")
        return await self.repo.soft_delete(budget_id)


class AdminLeaveBalanceService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = LeaveBalanceAdminRepository(session, company_id)

    async def list_for_employee(self, employee_id: UUID):
        return await self.repo.list_for_employee(employee_id)

    async def get(self, balance_id: UUID):
        bal = await self.repo.get(balance_id)
        if bal is None:
            raise NotFoundError("Leave balance not found")
        return bal

    async def create(self, payload: AdminLeaveBalanceCreate):
        existing = await self.repo.list_for_employee(payload.employee_id)
        for bal in existing:
            if bal.leave_type == payload.leave_type and bal.year == payload.year:
                raise ConflictError(
                    "Leave balance already exists for this employee, type, and year"
                )
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, balance_id: UUID, payload: AdminLeaveBalanceUpdate):
        bal = await self.repo.get(balance_id)
        if bal is None:
            raise NotFoundError("Leave balance not found")
        values = payload.model_dump(exclude_unset=True)
        updated = await self.repo.update(balance_id, values)
        if updated is None:
            raise NotFoundError("Leave balance not found")
        return updated

    async def delete(self, balance_id: UUID) -> bool:
        bal = await self.repo.get(balance_id)
        if bal is None:
            raise NotFoundError("Leave balance not found")
        return await self.repo.delete(balance_id)


class AdminHolidayService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = CompanyHolidayAdminRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, holiday_id: UUID):
        h = await self.repo.get(holiday_id)
        if h is None:
            raise NotFoundError("Holiday not found")
        return h

    async def create(self, payload: AdminHolidayCreate):
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, holiday_id: UUID, payload: AdminHolidayUpdate):
        h = await self.repo.get(holiday_id)
        if h is None:
            raise NotFoundError("Holiday not found")
        values = payload.model_dump(exclude_unset=True)
        updated = await self.repo.update(holiday_id, values)
        if updated is None:
            raise NotFoundError("Holiday not found")
        return updated

    async def hard_delete(self, holiday_id: UUID) -> bool:
        h = await self.repo.get(holiday_id)
        if h is None:
            raise NotFoundError("Holiday not found")
        return await self.repo.hard_delete(holiday_id)


class AdminStaffingRuleService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = StaffingRuleAdminRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, rule_id: UUID):
        r = await self.repo.get(rule_id)
        if r is None:
            raise NotFoundError("Staffing rule not found")
        return r

    async def create(self, payload: AdminStaffingRuleCreate):
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, rule_id: UUID, payload: AdminStaffingRuleUpdate):
        r = await self.repo.get(rule_id)
        if r is None:
            raise NotFoundError("Staffing rule not found")
        values = payload.model_dump(exclude_unset=True)
        updated = await self.repo.update(rule_id, values)
        if updated is None:
            raise NotFoundError("Staffing rule not found")
        return updated

    async def hard_delete(self, rule_id: UUID) -> bool:
        r = await self.repo.get(rule_id)
        if r is None:
            raise NotFoundError("Staffing rule not found")
        return await self.repo.hard_delete(rule_id)


class AdminSupplierService:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id
        self.repo = SupplierRepository(session, company_id)

    async def list(self, **filters):
        return await self.repo.list(**filters)

    async def get(self, supplier_id: UUID):
        s = await self.repo.get(supplier_id)
        if s is None:
            raise NotFoundError("Supplier not found")
        return s

    async def create(self, payload: AdminSupplierCreate):
        duplicate = await self.repo.get_by_name(payload.name)
        if duplicate is not None:
            raise ConflictError("Supplier name already exists")
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, supplier_id: UUID, payload: AdminSupplierUpdate):
        s = await self.repo.get(supplier_id)
        if s is None:
            raise NotFoundError("Supplier not found")
        values = payload.model_dump(exclude_unset=True)
        if "name" in values:
            duplicate = await self.repo.get_by_name(values["name"])
            if duplicate is not None and duplicate.id != supplier_id:
                raise ConflictError("Supplier name already exists")
        updated = await self.repo.update(supplier_id, values)
        if updated is None:
            raise NotFoundError("Supplier not found")
        return updated

    async def soft_delete(self, supplier_id: UUID) -> bool:
        s = await self.repo.get(supplier_id)
        if s is None:
            raise NotFoundError("Supplier not found")
        return await self.repo.delete(supplier_id)
