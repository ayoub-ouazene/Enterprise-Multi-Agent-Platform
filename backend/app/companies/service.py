from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.passwords import hash_password
from app.auth.service import AuthenticationService, TokenPair
from app.companies.models import Company
from app.companies.repository import CompanyRepository
from app.companies.schemas import (
    CompanyCreate,
    CompanyRegistrationRequest,
    CompanyUpdate,
)
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import ConflictError, NotFoundError
from app.departments.repository import DepartmentRepository
from app.users.repository import UserRepository


DEPARTMENT_NAMES: dict[DepartmentType, str] = {
    DepartmentType.CUSTOMER_SUPPORT: "Customer Support",
    DepartmentType.HR: "Human Resources",
    DepartmentType.IT: "Information Technology",
    DepartmentType.FINANCE: "Finance",
    DepartmentType.PROCUREMENT: "Procurement",
}


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

    async def register(
        self,
        payload: CompanyRegistrationRequest,
        settings: Settings,
    ) -> TokenPair:
        """Create an inactive tenant and its restricted onboarding account atomically."""
        slug = payload.company_slug.strip().lower()
        email = str(payload.email).strip().casefold()
        try:
            if await self.repository.get_by_slug(slug) is not None:
                raise ConflictError("Company workspace already exists")

            company = await self.repository.create(
                {
                    "name": payload.company_name.strip(),
                    "slug": slug,
                    "is_active": False,
                    "custom_data": {},
                }
            )
            user = await UserRepository(self.session, company.id).create(
                email=email,
                actor_type=ActorType.COMPANY,
                is_active=True,
                password_hash=hash_password(payload.password.get_secret_value()),
                must_change_password=False,
            )
            departments = DepartmentRepository(self.session, company.id)
            for department_type, name in DEPARTMENT_NAMES.items():
                await departments.create(
                    name=name,
                    department_type=department_type,
                    is_active=False,
                    custom_data={},
                )

            context = AuthenticatedUser(
                user_id=user.id,
                company_id=company.id,
                email=user.email,
                actor_type=ActorType.COMPANY,
                company_active=False,
                onboarding_complete=False,
            )
            tokens = await AuthenticationService(
                self.session,
                settings,
            ).issue_token_pair(context)
            await self.session.commit()
            return tokens
        except ConflictError:
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Company workspace already exists") from None
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
