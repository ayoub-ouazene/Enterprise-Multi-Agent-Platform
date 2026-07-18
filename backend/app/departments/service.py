from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.departments.models import Department
from app.departments.repository import DepartmentRepository
from app.departments.schemas import DepartmentCreate, DepartmentUpdate


class DepartmentService:
    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
        repository: DepartmentRepository | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.repository = repository or DepartmentRepository(session, company_id)

    async def get(self, department_id: UUID) -> Department:
        department = await self.repository.get_by_id(department_id)
        if department is None:
            raise NotFoundError("Department not found")
        return department

    async def create(self, payload: DepartmentCreate) -> Department:
        try:
            if await self.repository.get_by_type(payload.department_type) is not None:
                raise ConflictError("Department type already exists in this company")
            department = await self.repository.create(
                name=payload.name.strip(),
                department_type=payload.department_type,
                is_active=payload.is_active,
                custom_data=payload.custom_data,
            )
            await self.session.commit()
            await self.session.refresh(department)
            return department
        except ConflictError:
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Department type already exists in this company"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def update(
        self,
        department_id: UUID,
        payload: DepartmentUpdate,
    ) -> Department:
        try:
            if await self.repository.get_by_id(department_id) is None:
                raise NotFoundError("Department not found")
            values = payload.model_dump(exclude_unset=True)
            if values.get("name") is not None:
                values["name"] = str(values["name"]).strip()
            if values.get("department_type") is not None:
                existing = await self.repository.get_by_type(values["department_type"])
                if existing is not None and existing.id != department_id:
                    raise ConflictError(
                        "Department type already exists in this company"
                    )
            values = {key: value for key, value in values.items() if value is not None}

            department = await self.repository.update(department_id, values)
            if department is None:
                raise NotFoundError("Department not found")
            await self.session.commit()
            await self.session.refresh(department)
            return department
        except (ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "Department update conflicts with existing data"
            ) from None
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, department_id: UUID) -> None:
        try:
            if not await self.repository.delete(department_id):
                raise NotFoundError("Department not found")
            await self.session.commit()
        except NotFoundError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise
