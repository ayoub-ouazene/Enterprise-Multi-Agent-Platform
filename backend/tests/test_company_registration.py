import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

import app.companies.service as companies_service_module
import app.main as main_module
from app.auth.service import TokenPair
from app.companies.schemas import CompanyRegistrationRequest
from app.companies.service import CompanyService
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import ConflictError
from app.database.session import get_db_session


def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
        cors_origins=["http://localhost:5173"],
    )


def application(monkeypatch):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    app = main_module.create_app(settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    return app


def test_registration_endpoint_returns_onboarding_tokens(monkeypatch) -> None:
    pair = TokenPair("access", "refresh", 1800, 604800)

    async def register(_self, payload, _settings):
        assert payload.company_slug == "northwind"
        assert payload.password.get_secret_value() == "correct horse battery staple"
        return pair

    monkeypatch.setattr(CompanyService, "register", register)
    app = application(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/companies/register",
            json={
                "company_name": "Northwind",
                "company_slug": "northwind",
                "email": "owner@northwind.example.com",
                "password": "correct horse battery staple",
            },
        )

    assert response.status_code == 201
    assert response.json()["access_token"] == "access"
    assert "password" not in response.text


def test_duplicate_workspace_is_a_safe_conflict(monkeypatch) -> None:
    async def reject(*_args, **_kwargs):
        raise ConflictError("internal uniqueness detail")

    monkeypatch.setattr(CompanyService, "register", reject)
    app = application(monkeypatch)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/companies/register",
            json={
                "company_name": "Northwind",
                "company_slug": "northwind",
                "email": "owner@northwind.example.com",
                "password": "correct horse battery staple",
            },
        )

    assert response.status_code == 409
    assert response.json() == {"detail": "Company workspace already exists"}


def test_registration_service_creates_inactive_tenant_and_five_departments(
    monkeypatch,
) -> None:
    session = AsyncMock(spec=AsyncSession)
    company = SimpleNamespace(id=uuid4(), is_active=False)
    company_repo = Mock()
    company_repo.get_by_slug = AsyncMock(return_value=None)
    company_repo.create = AsyncMock(return_value=company)

    user = SimpleNamespace(id=uuid4(), email="owner@northwind.example.com")
    user_repo = Mock()
    user_repo.create = AsyncMock(return_value=user)
    user_repo_cls = Mock(return_value=user_repo)
    department_repo = Mock()
    department_repo.create = AsyncMock()
    department_repo_cls = Mock(return_value=department_repo)
    auth_service = Mock()
    auth_service.issue_token_pair = AsyncMock(
        return_value=TokenPair("access", "refresh", 1800, 604800)
    )

    monkeypatch.setattr(companies_service_module, "UserRepository", user_repo_cls)
    monkeypatch.setattr(
        companies_service_module,
        "DepartmentRepository",
        department_repo_cls,
    )
    monkeypatch.setattr(
        companies_service_module,
        "AuthenticationService",
        Mock(return_value=auth_service),
    )

    payload = CompanyRegistrationRequest(
        company_name="Northwind",
        company_slug="northwind",
        email="owner@northwind.example.com",
        password="correct horse battery staple",
    )
    asyncio.run(CompanyService(session, company_repo).register(payload, settings()))

    assert company_repo.create.await_args.args[0]["is_active"] is False
    assert user_repo.create.await_args.kwargs["actor_type"] == ActorType.COMPANY
    assert department_repo.create.await_count == len(DepartmentType)
    assert {
        call.kwargs["department_type"]
        for call in department_repo.create.await_args_list
    } == set(DepartmentType)
    assert all(
        call.kwargs["is_active"] is False
        for call in department_repo.create.await_args_list
    )
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
