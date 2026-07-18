from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DepartmentType
from app.departments.models import Department


class DepartmentRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, department_id: UUID) -> Department | None:
        return await self.session.scalar(
            select(Department).where(
                Department.id == department_id,
                Department.company_id == self.company_id,
            )
        )

    async def get_by_type(
        self,
        department_type: DepartmentType,
    ) -> Department | None:
        return await self.session.scalar(
            select(Department).where(
                Department.department_type == department_type,
                Department.company_id == self.company_id,
            )
        )

    async def list(self) -> list[Department]:
        result = await self.session.scalars(
            select(Department)
            .where(Department.company_id == self.company_id)
            .order_by(Department.name)
        )
        return list(result.all())

    async def create(
        self,
        *,
        name: str,
        department_type: DepartmentType,
        is_active: bool,
        custom_data: dict[str, object],
    ) -> Department:
        department = Department(
            company_id=self.company_id,
            name=name,
            department_type=department_type,
            is_active=is_active,
            custom_data=custom_data,
        )
        self.session.add(department)
        await self.session.flush()
        return department

    async def update(
        self,
        department_id: UUID,
        values: dict[str, object],
    ) -> Department | None:
        if not values:
            return await self.get_by_id(department_id)
        statement = (
            update(Department)
            .where(
                Department.id == department_id,
                Department.company_id == self.company_id,
            )
            .values(**values)
            .returning(Department)
        )
        return await self.session.scalar(statement)

    async def delete(self, department_id: UUID) -> bool:
        result = await self.session.execute(
            delete(Department).where(
                Department.id == department_id,
                Department.company_id == self.company_id,
            )
        )
        return bool(result.rowcount)
