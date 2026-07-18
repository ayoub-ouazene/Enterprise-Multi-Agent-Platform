from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessValidationError, ConflictError, NotFoundError
from app.departments.repository import DepartmentRepository
from app.employees.models import Employee
from app.employees.repository import EmployeeRepository
from app.employees.schemas import EmployeeCreate, EmployeeUpdate
from app.users.repository import UserRepository


class EmployeeService:
    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
        repository: EmployeeRepository | None = None,
        user_repository: UserRepository | None = None,
        department_repository: DepartmentRepository | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.repository = repository or EmployeeRepository(session, company_id)
        self.user_repository = user_repository or UserRepository(session, company_id)
        self.department_repository = department_repository or DepartmentRepository(
            session,
            company_id,
        )

    async def get(self, employee_id: UUID) -> Employee:
        employee = await self.repository.get_by_id(employee_id)
        if employee is None:
            raise NotFoundError("Employee not found")
        return employee

    async def _validate_user(
        self,
        user_id: UUID | None,
        employee_id: UUID | None = None,
    ) -> None:
        if user_id is None:
            return
        if await self.user_repository.get_by_id(user_id) is None:
            raise NotFoundError("User not found")
        existing = await self.repository.get_by_user_id(user_id)
        if existing is not None and existing.id != employee_id:
            raise ConflictError("User already has an employee profile")

    async def _validate_department(self, department_id: UUID | None) -> None:
        if (
            department_id is not None
            and await self.department_repository.get_by_id(department_id) is None
        ):
            raise NotFoundError("Department not found")

    async def _validate_manager(
        self,
        manager_employee_id: UUID | None,
        employee_id: UUID | None = None,
    ) -> None:
        if manager_employee_id is None:
            return
        if manager_employee_id == employee_id:
            raise BusinessValidationError("An employee cannot manage themselves")
        if await self.repository.get_by_id(manager_employee_id) is None:
            raise NotFoundError("Manager employee not found")

    async def create(self, payload: EmployeeCreate) -> Employee:
        employee_code = payload.employee_code.strip()
        try:
            if await self.repository.get_by_code(employee_code) is not None:
                raise ConflictError("Employee code already exists in this company")
            await self._validate_user(payload.user_id)
            await self._validate_department(payload.department_id)
            await self._validate_manager(payload.manager_employee_id)

            employee = await self.repository.create(
                user_id=payload.user_id,
                department_id=payload.department_id,
                employee_code=employee_code,
                job_title=payload.job_title.strip() if payload.job_title else None,
                manager_employee_id=payload.manager_employee_id,
                employment_status=payload.employment_status,
                custom_data=payload.custom_data,
            )
            await self.session.commit()
            await self.session.refresh(employee)
            return employee
        except (BusinessValidationError, ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Employee conflicts with existing company data"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def update(
        self,
        employee_id: UUID,
        payload: EmployeeUpdate,
    ) -> Employee:
        try:
            if await self.repository.get_by_id(employee_id) is None:
                raise NotFoundError("Employee not found")

            values = payload.model_dump(exclude_unset=True)
            if "employee_code" in values:
                if values["employee_code"] is None:
                    values.pop("employee_code")
                else:
                    employee_code = str(values["employee_code"]).strip()
                    existing = await self.repository.get_by_code(employee_code)
                    if existing is not None and existing.id != employee_id:
                        raise ConflictError(
                            "Employee code already exists in this company"
                        )
                    values["employee_code"] = employee_code

            if "user_id" in payload.model_fields_set:
                await self._validate_user(payload.user_id, employee_id)
            if "department_id" in payload.model_fields_set:
                await self._validate_department(payload.department_id)
            if "manager_employee_id" in payload.model_fields_set:
                await self._validate_manager(
                    payload.manager_employee_id,
                    employee_id,
                )
            if values.get("job_title") is not None:
                values["job_title"] = str(values["job_title"]).strip()
            if values.get("employment_status") is None:
                values.pop("employment_status", None)
            if values.get("custom_data") is None:
                values.pop("custom_data", None)

            employee = await self.repository.update(employee_id, values)
            if employee is None:
                raise NotFoundError("Employee not found")
            await self.session.commit()
            await self.session.refresh(employee)
            return employee
        except (BusinessValidationError, ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Employee update conflicts with existing company data"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, employee_id: UUID) -> None:
        try:
            if not await self.repository.delete(employee_id):
                raise NotFoundError("Employee not found")
            await self.session.commit()
        except NotFoundError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise
