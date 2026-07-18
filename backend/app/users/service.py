from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.users.models import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
        repository: UserRepository | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.repository = repository or UserRepository(session, company_id)

    async def get(self, user_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def create(self, payload: UserCreate) -> User:
        email = str(payload.email).strip().casefold()
        try:
            if await self.repository.get_by_email(email) is not None:
                raise ConflictError("Email already exists in this company")
            user = await self.repository.create(
                email=email,
                actor_type=payload.actor_type,
                is_active=payload.is_active,
            )
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except ConflictError:
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("Email already exists in this company") from None
        except Exception:
            await self.session.rollback()
            raise

    async def update(self, user_id: UUID, payload: UserUpdate) -> User:
        try:
            if await self.repository.get_by_id(user_id) is None:
                raise NotFoundError("User not found")
            values = payload.model_dump(exclude_unset=True)
            if values.get("email") is not None:
                email = str(values["email"]).strip().casefold()
                existing = await self.repository.get_by_email(email)
                if existing is not None and existing.id != user_id:
                    raise ConflictError("Email already exists in this company")
                values["email"] = email
            values = {key: value for key, value in values.items() if value is not None}

            user = await self.repository.update(user_id, values)
            if user is None:
                raise NotFoundError("User not found")
            await self.session.commit()
            await self.session.refresh(user)
            return user
        except (ConflictError, NotFoundError):
            await self.session.rollback()
            raise
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError("User update conflicts with existing data") from None
        except Exception:
            await self.session.rollback()
            raise

    async def delete(self, user_id: UUID) -> None:
        try:
            if not await self.repository.delete(user_id):
                raise NotFoundError("User not found")
            await self.session.commit()
        except NotFoundError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise
