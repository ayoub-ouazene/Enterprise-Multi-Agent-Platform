from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.passwords import verify_password, validate_new_password, hash_password
from app.auth.repository import RefreshTokenRepository, hash_token_identifier
from app.auth.tokens import (
    EncodedToken,
    TokenValidationError,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.companies.repository import CompanyRepository
from app.core.config import Settings
from app.core.enums import ActorType
from app.users.models import User
from app.users.repository import UserRepository


GENERIC_AUTHENTICATION_ERROR = "Invalid authentication credentials"


class AuthenticationError(ValueError):
    """A deliberately generic authentication failure safe for API responses."""


class WorkspaceNotFoundError(AuthenticationError):
    """Raised when a public workspace slug does not exist."""


class InactiveUserError(AuthenticationError):
    """Raised only after the supplied password has been verified."""


class CompanyInactiveError(AuthenticationError):
    """Raised when a non-Company actor tries to enter an inactive tenant."""


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    access_token_expires_in: int
    refresh_token_expires_in: int


UserRepositoryFactory = Callable[[UUID], UserRepository]


class AuthenticationService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        company_repository: CompanyRepository | None = None,
        refresh_repository: RefreshTokenRepository | None = None,
        user_repository_factory: UserRepositoryFactory | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.company_repository = company_repository or CompanyRepository(session)
        self.refresh_repository = refresh_repository or RefreshTokenRepository(session)
        self.user_repository_factory = user_repository_factory or (
            lambda company_id: UserRepository(session, company_id)
        )

    @staticmethod
    def _context_from_user(user: User, *, company_active: bool = True) -> AuthenticatedUser:
        employee = user.employee
        if employee is not None and employee.company_id != user.company_id:
            raise AuthenticationError(GENERIC_AUTHENTICATION_ERROR)
        employee_id = employee.id if employee is not None else None
        department_id = employee.department_id if employee is not None else None
        is_manager = (
            user.actor_type == ActorType.DEPARTMENT_MANAGER
            and employee_id is not None
            and department_id is not None
        )
        return AuthenticatedUser(
            user_id=user.id,
            company_id=user.company_id,
            email=user.email,
            actor_type=user.actor_type,
            employee_id=employee_id,
            department_id=department_id,
            is_manager=is_manager,
            company_active=company_active,
            onboarding_complete=company_active,
            must_change_password=bool(
                getattr(user, "must_change_password", False)
            ),
        )

    @staticmethod
    def _reject() -> AuthenticationError:
        return AuthenticationError(GENERIC_AUTHENTICATION_ERROR)

    async def login(self, company_slug: str, email: str, password: str) -> TokenPair:
        try:
            company = await self.company_repository.get_by_slug(
                company_slug.strip().lower()
            )
            if company is None:
                verify_password(password, None)
                raise WorkspaceNotFoundError("Company workspace was not found")

            user_repository = self.user_repository_factory(company.id)
            user = await user_repository.get_by_email_with_employee(
                email.strip().casefold()
            )
            password_is_valid = verify_password(
                password,
                user.password_hash if user is not None else None,
            )
            if user is None or not password_is_valid or user.company_id != company.id:
                raise self._reject()
            if not user.is_active:
                raise InactiveUserError("User account is inactive")
            if not company.is_active and user.actor_type != ActorType.COMPANY:
                raise CompanyInactiveError("Company workspace is not active")

            context = self._context_from_user(
                user,
                company_active=company.is_active,
            )
            token_pair = await self._issue_token_pair(context)
            await self.session.commit()
            return token_pair
        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def refresh(self, token: str) -> TokenPair:
        try:
            try:
                claims = decode_refresh_token(token, self.settings)
            except TokenValidationError:
                raise self._reject() from None

            now = datetime.now(UTC)
            current = await self.refresh_repository.get_for_rotation(
                jti_hash=hash_token_identifier(claims.jti),
                company_id=claims.company_id,
                user_id=claims.sub,
            )
            if current is None or current.revoked_at is not None:
                raise self._reject()
            database_expiration = current.expires_at
            if database_expiration.tzinfo is None:
                database_expiration = database_expiration.replace(tzinfo=UTC)
            if database_expiration <= now:
                raise self._reject()

            company = await self.company_repository.get_by_id(claims.company_id)
            user = await self.user_repository_factory(
                claims.company_id
            ).get_by_id_with_employee(claims.sub)
            if company is None or user is None or user.company_id != claims.company_id:
                raise self._reject()
            if not user.is_active:
                raise InactiveUserError("User account is inactive")
            if not company.is_active and user.actor_type != ActorType.COMPANY:
                raise CompanyInactiveError("Company workspace is not active")

            context = self._context_from_user(
                user,
                company_active=company.is_active,
            )
            access = create_access_token(context, self.settings, now=now)
            replacement = create_refresh_token(context, self.settings, now=now)
            replacement_record = await self.refresh_repository.create(
                company_id=context.company_id,
                user_id=context.user_id,
                jti_hash=hash_token_identifier(replacement.jti),
                expires_at=replacement.expires_at,
            )
            revoked = await self.refresh_repository.revoke(
                token_id=current.id,
                company_id=context.company_id,
                user_id=context.user_id,
                revoked_at=now,
                replaced_by_token_id=replacement_record.id,
            )
            if not revoked:
                raise self._reject()

            await self.session.commit()
            return self._token_pair(access, replacement, now)
        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def change_password(
        self,
        user_id: UUID,
        company_id: UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        try:
            user_repository = self.user_repository_factory(company_id)
            user = await user_repository.get_by_id(user_id)
            if user is None or not user.is_active:
                raise self._reject()

            if not verify_password(current_password, user.password_hash):
                raise self._reject()

            validate_new_password(new_password)
            new_hash = hash_password(new_password)
            updated = await user_repository.update(
                user_id,
                {
                    "password_hash": new_hash,
                    "must_change_password": False,
                },
            )
            if updated is None:
                raise self._reject()

            await self.session.commit()
        except AuthenticationError:
            await self.session.rollback()
            raise
        except Exception:
            await self.session.rollback()
            raise

    async def authenticate_access_token(
        self,
        token: str,
        *,
        allow_inactive_company: bool = False,
    ) -> AuthenticatedUser:
        try:
            claims = decode_access_token(token, self.settings)
        except TokenValidationError:
            raise self._reject() from None

        company = await self.company_repository.get_by_id(claims.company_id)
        user = await self.user_repository_factory(
            claims.company_id
        ).get_by_id_with_employee(claims.sub)
        if company is None or user is None or user.company_id != claims.company_id:
            raise self._reject()
        if not user.is_active:
            raise InactiveUserError("User account is inactive")
        if not company.is_active and (
            user.actor_type != ActorType.COMPANY or not allow_inactive_company
        ):
            raise CompanyInactiveError("Company workspace is not active")
        return self._context_from_user(user, company_active=company.is_active)

    async def issue_token_pair(self, context: AuthenticatedUser) -> TokenPair:
        """Issue tokens inside a caller-controlled transaction."""
        return await self._issue_token_pair(context)

    async def _issue_token_pair(self, context: AuthenticatedUser) -> TokenPair:
        now = datetime.now(UTC)
        access = create_access_token(context, self.settings, now=now)
        refresh = create_refresh_token(context, self.settings, now=now)
        await self.refresh_repository.create(
            company_id=context.company_id,
            user_id=context.user_id,
            jti_hash=hash_token_identifier(refresh.jti),
            expires_at=refresh.expires_at,
        )
        return self._token_pair(access, refresh, now)

    @staticmethod
    def _token_pair(
        access: EncodedToken,
        refresh: EncodedToken,
        now: datetime,
    ) -> TokenPair:
        return TokenPair(
            access_token=access.value,
            refresh_token=refresh.value,
            access_token_expires_in=int((access.expires_at - now).total_seconds()),
            refresh_token_expires_in=int((refresh.expires_at - now).total_seconds()),
        )
