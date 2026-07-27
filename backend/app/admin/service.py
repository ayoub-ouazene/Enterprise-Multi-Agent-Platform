"""Admin service — business logic for company data management."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.departments.hr.models import CompanyHoliday, DepartmentStaffingRule
from app.departments.it.enums import AssetStatus
from app.departments.it.models import Asset
from app.departments.repository import DepartmentRepository
from app.employees.models import Employee
from app.human_actions.models import HumanAction
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
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Employee]:
        return await self.repo.list(
            department_id=department_id, status=status, q=q, limit=limit, offset=offset
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
        if await self.repo.get_by_email(payload.email):
            raise ConflictError("Employee email already exists")

        department_id = payload.department_id
        if department_id is not None:
            department = await DepartmentRepository(
                self.session, self.company_id
            ).get_by_id(department_id)
            if department is None or not department.is_active:
                raise BusinessValidationError(
                    "Selected department is not active or available"
                )

        if payload.temporary_password is None:
            raise BusinessValidationError(
                "A temporary password is required when creating an employee"
            )
        password_hash = hash_password(
            payload.temporary_password.get_secret_value()
        )
        user = User(
            company_id=self.company_id,
            email=payload.email,
            password_hash=password_hash,
            actor_type=ActorType.EMPLOYEE,
            is_active=True,
            must_change_password=True,
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
        emp.user = user
        return emp

    async def update(
        self,
        employee_id: UUID,
        payload: AdminEmployeeUpdate,
    ) -> Employee:
        emp = await self.repo.get(employee_id)
        if emp is None:
            raise NotFoundError("Employee not found")
        if payload.employment_status == EmploymentStatus.TERMINATED:
            raise BusinessValidationError(
                "Use the employee deactivation operation so assignment blockers are enforced"
            )
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
        if payload.email is not None:
            duplicate = await self.repo.get_by_email(payload.email)
            if duplicate is not None and duplicate.id != employee_id:
                raise ConflictError("Employee email already exists")
            if emp.user_id is None:
                raise BusinessValidationError("Employee account is not provisioned")
            await self.session.execute(
                update(User)
                .where(
                    User.id == emp.user_id,
                    User.company_id == self.company_id,
                )
                .values(email=payload.email.strip().lower())
            )
        if payload.manager_employee_id is not None:
            manager = await self.repo.get(payload.manager_employee_id)
            if (
                manager is None
                or manager.user_id is None
                or manager.employment_status != EmploymentStatus.ACTIVE
            ):
                raise BusinessValidationError("Selected manager is not available")
            if manager.id == employee_id:
                raise BusinessValidationError("An employee cannot manage themselves")
            ancestor = manager
            visited: set[UUID] = {employee_id}
            while ancestor.manager_employee_id is not None:
                if ancestor.id in visited:
                    raise BusinessValidationError(
                        "Manager assignment would create a reporting cycle"
                    )
                visited.add(ancestor.id)
                next_manager = await self.repo.get(ancestor.manager_employee_id)
                if next_manager is None:
                    break
                if next_manager.id in visited:
                    raise BusinessValidationError(
                        "Manager assignment would create a reporting cycle"
                    )
                ancestor = next_manager
        updated = await self.repo.update(employee_id, values)
        if updated is None:
            raise NotFoundError("Employee not found")
        refreshed = await self.repo.get(employee_id)
        if refreshed is None:
            raise NotFoundError("Employee not found")
        return refreshed

    async def soft_delete(self, employee_id: UUID) -> bool:
        emp = await self.repo.get(employee_id)
        if emp is None:
            raise NotFoundError("Employee not found")
        if emp.user and emp.user.actor_type == ActorType.DEPARTMENT_MANAGER:
            raise ConflictError(
                "Assign a replacement department manager before deactivating this employee"
            )
        assigned_assets = await self.session.scalar(
            select(func.count(Asset.id)).where(
                Asset.company_id == self.company_id,
                Asset.assigned_employee_id == employee_id,
                Asset.status == AssetStatus.ASSIGNED,
            )
        )
        if assigned_assets:
            raise ConflictError(
                "Unassign the employee's active assets before deactivation"
            )
        if emp.user_id is not None:
            pending_actions = await self.session.scalar(
                select(func.count(HumanAction.id)).where(
                    HumanAction.company_id == self.company_id,
                    HumanAction.assigned_user_id == emp.user_id,
                    HumanAction.status == "pending",
                )
            )
            if pending_actions:
                raise ConflictError(
                    "Resolve or reassign pending human actions before deactivation"
                )
            await self.session.execute(
                update(User)
                .where(
                    User.id == emp.user_id,
                    User.company_id == self.company_id,
                )
                .values(is_active=False)
            )
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
        if values.get("is_active") is False:
            member_count = await self.session.scalar(
                select(func.count(Employee.id)).where(
                    Employee.company_id == self.company_id,
                    Employee.department_id == department_id,
                    Employee.employment_status == EmploymentStatus.ACTIVE,
                )
            )
            if member_count:
                raise ConflictError(
                    "Move or deactivate active department members before disabling it"
                )
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
        values = payload.model_dump(exclude_unset=True)
        await self._validate_assignment(values)
        return await self.repo.create(values)

    async def update(self, asset_id: UUID, payload: AdminAssetUpdate):
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        values = payload.model_dump(exclude={"version"}, exclude_unset=True)
        if asset.status == AssetStatus.RETIRED:
            raise BusinessValidationError("Retired assets are read-only")
        await self._validate_assignment(values)
        if values.get("status") == AssetStatus.RETIRED and (
            asset.assigned_employee_id is not None
            or values.get("assigned_employee_id") is not None
        ):
            raise ConflictError("Unassign the asset before retirement")
        updated = await self.repo.update(asset_id, values, payload.version)
        if updated is None:
            raise OptimisticLockError("Asset was modified by another user")
        return updated

    async def soft_delete(self, asset_id: UUID) -> bool:
        asset = await self.repo.get(asset_id)
        if asset is None:
            raise NotFoundError("Asset not found")
        if asset.assigned_employee_id is not None:
            raise ConflictError("Unassign the asset before retirement")
        return await self.repo.soft_delete(asset_id)

    async def _validate_assignment(self, values: dict[str, object]) -> None:
        employee_id = values.get("assigned_employee_id")
        status = values.get("status")
        if employee_id is not None:
            employee = await EmployeeAdminRepository(
                self.session, self.company_id
            ).get(employee_id)
            if employee is None or employee.employment_status != EmploymentStatus.ACTIVE:
                raise BusinessValidationError(
                    "Assets may be assigned only to active company employees"
                )
            if status not in (None, AssetStatus.ASSIGNED):
                raise BusinessValidationError(
                    "An assigned asset must use the assigned status"
                )
            values["status"] = AssetStatus.ASSIGNED
        elif status == AssetStatus.ASSIGNED:
            raise BusinessValidationError("Assigned status requires an active employee")
        elif "assigned_employee_id" in values and status is None:
            values["status"] = AssetStatus.AVAILABLE


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
        duplicate = await self.session.scalar(
            select(CompanyHoliday.id).where(
                CompanyHoliday.company_id == self.company_id,
                CompanyHoliday.holiday_date == payload.holiday_date,
            )
        )
        if duplicate is not None:
            raise ConflictError("A company holiday already exists on this date")
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, holiday_id: UUID, payload: AdminHolidayUpdate):
        h = await self.repo.get(holiday_id)
        if h is None:
            raise NotFoundError("Holiday not found")
        values = payload.model_dump(exclude_unset=True)
        if payload.holiday_date is not None:
            duplicate = await self.session.scalar(
                select(CompanyHoliday.id).where(
                    CompanyHoliday.company_id == self.company_id,
                    CompanyHoliday.holiday_date == payload.holiday_date,
                    CompanyHoliday.id != holiday_id,
                )
            )
            if duplicate is not None:
                raise ConflictError("A company holiday already exists on this date")
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
        await self._validate_scope_and_overlap(payload)
        return await self.repo.create(payload.model_dump(exclude_unset=True))

    async def update(self, rule_id: UUID, payload: AdminStaffingRuleUpdate):
        r = await self.repo.get(rule_id)
        if r is None:
            raise NotFoundError("Staffing rule not found")
        values = payload.model_dump(exclude_unset=True)
        department_id = r.department_id
        effective_from = payload.effective_from or r.effective_from
        effective_to = (
            payload.effective_to
            if "effective_to" in payload.model_fields_set
            else r.effective_to
        )
        await self._validate_overlap(
            department_id, effective_from, effective_to, exclude_id=rule_id
        )
        updated = await self.repo.update(rule_id, values)
        if updated is None:
            raise NotFoundError("Staffing rule not found")
        return updated

    async def hard_delete(self, rule_id: UUID) -> bool:
        r = await self.repo.get(rule_id)
        if r is None:
            raise NotFoundError("Staffing rule not found")
        return await self.repo.hard_delete(rule_id)

    async def _validate_scope_and_overlap(
        self, payload: AdminStaffingRuleCreate
    ) -> None:
        department = await DepartmentRepository(
            self.session, self.company_id
        ).get_by_id(payload.department_id)
        if department is None:
            raise BusinessValidationError("Selected department is not available")
        await self._validate_overlap(
            payload.department_id, payload.effective_from, payload.effective_to
        )

    async def _validate_overlap(
        self,
        department_id: UUID,
        effective_from,
        effective_to,
        *,
        exclude_id: UUID | None = None,
    ) -> None:
        statement = select(DepartmentStaffingRule.id).where(
            DepartmentStaffingRule.company_id == self.company_id,
            DepartmentStaffingRule.department_id == department_id,
            DepartmentStaffingRule.is_active.is_(True),
            (
                DepartmentStaffingRule.effective_to.is_(None)
                | (DepartmentStaffingRule.effective_to >= effective_from)
            ),
        )
        if effective_to is not None:
            statement = statement.where(
                DepartmentStaffingRule.effective_from <= effective_to
            )
        if exclude_id is not None:
            statement = statement.where(DepartmentStaffingRule.id != exclude_id)
        if await self.session.scalar(statement) is not None:
            raise ConflictError(
                "An active staffing rule already covers this department and period"
            )


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
