from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.models import Company


class CompanyRepository:
    """Persistence for the root tenant entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, company_id: UUID) -> Company | None:
        return await self.session.scalar(
            select(Company).where(Company.id == company_id)
        )

    async def get_by_slug(self, slug: str) -> Company | None:
        return await self.session.scalar(select(Company).where(Company.slug == slug))

    async def list(self) -> list[Company]:
        result = await self.session.scalars(select(Company).order_by(Company.name))
        return list(result.all())

    async def create(self, values: dict[str, object]) -> Company:
        company = Company(**values)
        self.session.add(company)
        await self.session.flush()
        return company

    async def update(
        self,
        company_id: UUID,
        values: dict[str, object],
    ) -> Company | None:
        if not values:
            return await self.get_by_id(company_id)
        statement = (
            update(Company)
            .where(Company.id == company_id)
            .values(**values)
            .returning(Company)
        )
        return await self.session.scalar(statement)

    async def delete(self, company_id: UUID) -> bool:
        result = await self.session.execute(
            delete(Company).where(Company.id == company_id)
        )
        return bool(result.rowcount)
