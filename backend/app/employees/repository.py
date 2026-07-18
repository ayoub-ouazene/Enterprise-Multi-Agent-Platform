from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EmploymentStatus
from app.employees.models import Employee


class EmployeeRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        return await self.session.scalar(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == self.company_id,
            )
        )

    async def get_by_code(self, employee_code: str) -> Employee | None:
        return await self.session.scalar(
            select(Employee).where(
                Employee.employee_code == employee_code,
                Employee.company_id == self.company_id,
            )
        )

    async def get_by_user_id(self, user_id: UUID) -> Employee | None:
        return await self.session.scalar(
            select(Employee).where(
                Employee.user_id == user_id,
                Employee.company_id == self.company_id,
            )
        )

    async def list(self) -> list[Employee]:
        result = await self.session.scalars(
            select(Employee)
            .where(Employee.company_id == self.company_id)
            .order_by(Employee.employee_code)
        )
        return list(result.all())

    async def create(
        self,
        *,
        user_id: UUID | None,
        department_id: UUID | None,
        employee_code: str,
        job_title: str | None,
        manager_employee_id: UUID | None,
        employment_status: EmploymentStatus,
        custom_data: dict[str, object],
    ) -> Employee:
        employee = Employee(
            company_id=self.company_id,
            user_id=user_id,
            department_id=department_id,
            employee_code=employee_code,
            job_title=job_title,
            manager_employee_id=manager_employee_id,
            employment_status=employment_status,
            custom_data=custom_data,
        )
        self.session.add(employee)
        await self.session.flush()
        return employee

    async def update(
        self,
        employee_id: UUID,
        values: dict[str, object],
    ) -> Employee | None:
        if not values:
            return await self.get_by_id(employee_id)
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

    async def delete(self, employee_id: UUID) -> bool:
        result = await self.session.execute(
            delete(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == self.company_id,
            )
        )
        return bool(result.rowcount)
