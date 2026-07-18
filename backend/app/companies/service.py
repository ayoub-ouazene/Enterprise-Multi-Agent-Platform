from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.models import Company
from app.companies.repository import CompanyRepository
from app.companies.schemas import CompanyCreate, CompanyUpdate
from app.core.exceptions import ConflictError, NotFoundError


class CompanyService:
    def __init__(
        self,
        session: AsyncSession,
        repository: CompanyRepository | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or CompanyRepository(session)

    async def get(self, company_id: UUID) -> Company:
        company = await self.repository.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    async def create(self, payload: CompanyCreate) -> Company:
        slug = payload.slug.strip().lower()
        try:
            if await self.repository.get_by_slug(slug) is not None:
                raise ConflictError("Company slug already exists")
            values = payload.model_dump()
            values["name"] = payload.name.strip()
            values["slug"] = slug
            company = await self.repository.create(values)
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except ConflictError:
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Company slug already exists") from None
        except Exception:
            await self.session.rollback()
            raise

    async def update(self, company_id: UUID, payload: CompanyUpdate) -> Company:
        try:
            current = await self.repository.get_by_id(company_id)
            if current is None:
                raise NotFoundError("Company not found")

            values = payload.model_dump(exclude_unset=True)
            if values.get("name") is not None:
                values["name"] = str(values["name"]).strip()
            if values.get("slug") is not None:
                slug = str(values["slug"]).strip().lower()
                existing = await self.repository.get_by_slug(slug)
                if existing is not None and existing.id != company_id:
                    raise ConflictError("Company slug already exists")
                values["slug"] = slug
            values = {key: value for key, value in values.items() if value is not None}

            company = await self.repository.update(company_id, values)
            if company is None:
                raise NotFoundError("Company not found")
            await self.session.commit()
            await self.session.refresh(company)
            return company
        except (ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Company update conflicts with existing data") from None
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, company_id: UUID) -> None:
        try:
            if not await self.repository.delete(company_id):
                raise NotFoundError("Company not found")
            await self.session.commit()
        except NotFoundError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise
