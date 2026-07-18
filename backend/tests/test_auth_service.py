import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.passwords import hash_password
from app.auth.repository import RefreshTokenRepository, hash_token_identifier
from app.auth.service import AuthenticationError, AuthenticationService
from app.auth.tokens import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
from app.companies.repository import CompanyRepository
from app.core.config import Settings
from app.core.enums import ActorType
from app.users.repository import UserRepository


PASSWORD = "correct horse battery staple"


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def company(*, active: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        name="Acme",
        slug="acme",
        is_active=active,
        custom_data={},
    )


def user(company_id, *, active: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        company_id=company_id,
        email="owner@example.com",
        password_hash=hash_password(PASSWORD),
        actor_type=ActorType.COMPANY,
        is_active=active,
        employee=None,
    )


def service_fixture(tenant, account):
    session = AsyncMock(spec=AsyncSession)
    companies = Mock(spec=CompanyRepository)
    companies.get_by_slug = AsyncMock(return_value=tenant)
    companies.get_by_id = AsyncMock(return_value=tenant)
    users = Mock(spec=UserRepository)
    users.get_by_email_with_employee = AsyncMock(return_value=account)
    users.get_by_id_with_employee = AsyncMock(return_value=account)
    user_factory = Mock(return_value=users)
    refresh_tokens = Mock(spec=RefreshTokenRepository)
    refresh_tokens.create = AsyncMock(
        side_effect=lambda **values: SimpleNamespace(id=uuid4(), **values)
    )
    refresh_tokens.get_for_rotation = AsyncMock()
    refresh_tokens.revoke = AsyncMock(return_value=True)
    service = AuthenticationService(
        session,
        build_settings(),
        company_repository=companies,
        refresh_repository=refresh_tokens,
        user_repository_factory=user_factory,
    )
    return service, session, companies, users, user_factory, refresh_tokens


def test_successful_login_creates_both_tokens_and_commits() -> None:
    tenant = company()
    account = user(tenant.id)
    service, session, _, _, _, refresh_tokens = service_fixture(tenant, account)

    pair = asyncio.run(service.login("acme", account.email, PASSWORD))

    assert decode_access_token(pair.access_token, build_settings()).sub == account.id
    assert decode_refresh_token(pair.refresh_token, build_settings()).sub == account.id
    refresh_tokens.create.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize("account_mode", ["missing", "wrong-password"])
def test_invalid_email_or_password_returns_generic_error(account_mode: str) -> None:
    tenant = company()
    account = None if account_mode == "missing" else user(tenant.id)
    service, session, _, _, _, _ = service_fixture(tenant, account)
    supplied_password = PASSWORD if account is None else "incorrect password"

    with pytest.raises(AuthenticationError, match="Invalid authentication credentials"):
        asyncio.run(service.login("acme", "unknown@example.com", supplied_password))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_inactive_user_is_rejected() -> None:
    tenant = company()
    service, session, *_ = service_fixture(tenant, user(tenant.id, active=False))

    with pytest.raises(AuthenticationError):
        asyncio.run(service.login("acme", "owner@example.com", PASSWORD))

    session.rollback.assert_awaited_once()


def test_inactive_company_is_rejected() -> None:
    tenant = company(active=False)
    service, session, *_ = service_fixture(tenant, user(tenant.id))

    with pytest.raises(AuthenticationError):
        asyncio.run(service.login("acme", "owner@example.com", PASSWORD))

    session.rollback.assert_awaited_once()


def test_login_is_scoped_to_the_company_resolved_from_slug() -> None:
    requested_tenant = company()
    service, _, _, _, user_factory, _ = service_fixture(requested_tenant, None)

    with pytest.raises(AuthenticationError):
        asyncio.run(service.login("acme", "shared@example.com", PASSWORD))

    user_factory.assert_called_once_with(requested_tenant.id)


def test_refresh_rotates_persisted_token_in_one_transaction() -> None:
    tenant = company()
    account = user(tenant.id)
    service, session, _, _, _, refresh_tokens = service_fixture(tenant, account)
    context = AuthenticatedUser(
        user_id=account.id,
        company_id=tenant.id,
        email=account.email,
        actor_type=account.actor_type,
    )
    original = create_refresh_token(context, build_settings())
    original_record = SimpleNamespace(
        id=uuid4(),
        company_id=tenant.id,
        user_id=account.id,
        jti_hash=hash_token_identifier(original.jti),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        revoked_at=None,
    )
    refresh_tokens.get_for_rotation.return_value = original_record

    pair = asyncio.run(service.refresh(original.value))

    assert pair.refresh_token != original.value
    assert decode_access_token(pair.access_token, build_settings()).sub == account.id
    assert decode_refresh_token(pair.refresh_token, build_settings()).sub == account.id
    refresh_tokens.get_for_rotation.assert_awaited_once_with(
        jti_hash=hash_token_identifier(original.jti),
        company_id=tenant.id,
        user_id=account.id,
    )
    refresh_tokens.revoke.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_access_token_context_is_rebuilt_from_tenant_scoped_database_user() -> None:
    tenant = company()
    account = user(tenant.id)
    service, _, _, _, user_factory, _ = service_fixture(tenant, account)
    stale_context = AuthenticatedUser(
        user_id=account.id,
        company_id=tenant.id,
        email=account.email,
        actor_type=ActorType.EMPLOYEE,
    )
    token = create_access_token(stale_context, build_settings()).value

    trusted = asyncio.run(service.authenticate_access_token(token))

    assert trusted.actor_type == ActorType.COMPANY
    assert trusted.company_id == tenant.id
    user_factory.assert_called_once_with(tenant.id)
