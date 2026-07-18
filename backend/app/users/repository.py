from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ActorType
from app.users.models import User
from app.employees.models import Employee


class UserRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.scalar(
            select(User).where(
                User.id == user_id,
                User.company_id == self.company_id,
            )
        )

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User).where(
                User.email == email,
                User.company_id == self.company_id,
            )
        )

    async def get_by_id_with_employee(self, user_id: UUID) -> User | None:
        return await self.session.scalar(
            select(User)
            .options(selectinload(User.employee))
            .where(
                User.id == user_id,
                User.company_id == self.company_id,
            )
        )

    async def get_by_email_with_employee(self, email: str) -> User | None:
        return await self.session.scalar(
            select(User)
            .options(selectinload(User.employee))
            .where(
                User.email == email,
                User.company_id == self.company_id,
            )
        )

    async def list(self) -> list[User]:
        result = await self.session.scalars(
            select(User).where(User.company_id == self.company_id).order_by(User.email)
        )
        return list(result.all())

    async def list_company_accounts(self) -> list[User]:
        result = await self.session.scalars(
            select(User).where(
                User.company_id == self.company_id,
                User.actor_type == ActorType.COMPANY,
                User.is_active.is_(True),
            )
        )
        return list(result.all())

    async def list_department_managers(self, department_id: UUID) -> list[User]:
        result = await self.session.scalars(
            select(User)
            .join(Employee, Employee.user_id == User.id)
            .where(
                User.company_id == self.company_id,
                User.actor_type == ActorType.DEPARTMENT_MANAGER,
                User.is_active.is_(True),
                Employee.company_id == self.company_id,
                Employee.department_id == department_id,
            )
        )
        return list(result.all())

    async def create(
        self,
        *,
        email: str,
        actor_type: ActorType,
        is_active: bool,
        password_hash: str | None = None,
    ) -> User:
        user = User(
            company_id=self.company_id,
            email=email,
            password_hash=password_hash,
            actor_type=actor_type,
            is_active=is_active,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update(
        self,
        user_id: UUID,
        values: dict[str, object],
    ) -> User | None:
        if not values:
            return await self.get_by_id(user_id)
        statement = (
            update(User)
            .where(
                User.id == user_id,
                User.company_id == self.company_id,
            )
            .values(**values)
            .returning(User)
        )
        return await self.session.scalar(statement)

    async def delete(self, user_id: UUID) -> bool:
        result = await self.session.execute(
            delete(User).where(
                User.id == user_id,
                User.company_id == self.company_id,
            )
        )
        return bool(result.rowcount)
