"""Onboarding API router tests."""
import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session
from app.onboarding.dependencies import require_company_account
from app.onboarding.enums import ImportJobStatus, ImportType
from app.onboarding.schemas import (
    ImportConfirmResponse,
    ImportValidateResponse,
    OnboardingStatusItem,
    OnboardingStatusResponse,
    RowValidationResult,
)
from app.onboarding.service import OnboardingService


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def company_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="admin@example.com",
        actor_type=ActorType.COMPANY,
    )


def employee_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="emp@example.com",
        actor_type=ActorType.EMPLOYEE,
        employee_id=uuid4(),
    )


def build_app(monkeypatch, user) -> TestClient:
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _settings: engine)
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        lambda _engine: Mock(),
    )
    app = main_module.create_app(build_settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return app


def _fake_service(fake_status=None, fake_import=None):
    """Return a mock OnboardingService-like object."""
    return SimpleNamespace(
        status_service=fake_status or Mock(),
        import_service=fake_import or Mock(),
    )


def test_status_endpoint_returns_typed_response(monkeypatch) -> None:
    user = company_user()
    fake_status = Mock()
    fake_status.get_status = AsyncMock(
        return_value=OnboardingStatusResponse(
            company_id=user.company_id,
            can_activate=False,
            is_active=False,
            items=[
                OnboardingStatusItem(
                    requirement="company_profile",
                    satisfied=True,
                    details=None,
                ),
            ],
        )
    )
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", fake_status
        ) or setattr(self, "import_service", Mock()),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/onboarding/status")

    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == str(user.company_id)
    assert data["can_activate"] is False
    assert len(data["items"]) == 1
    assert data["items"][0]["requirement"] == "company_profile"


def test_activate_requires_company_account(monkeypatch) -> None:
    user = employee_user()
    app = build_app(monkeypatch, user)
    app.dependency_overrides[require_company_account] = lambda: user

    with TestClient(app) as client:
        response = client.post("/api/v1/onboarding/activate")

    assert response.status_code == 403


def test_activate_success(monkeypatch) -> None:
    user = company_user()
    fake_status = Mock()
    fake_status.activate = AsyncMock(return_value=None)
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", fake_status
        ) or setattr(self, "import_service", Mock()),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post("/api/v1/onboarding/activate")

    assert response.status_code == 200
    assert response.json()["activated"] is True
    fake_status.activate.assert_awaited_once_with(user)


def test_validate_import_returns_row_results(monkeypatch) -> None:
    user = company_user()
    fake_import = Mock()
    fake_import.validate_import = AsyncMock(
        return_value=ImportValidateResponse(
            import_job_id=uuid4(),
            import_type=ImportType.DEPARTMENTS,
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            can_confirm=True,
            rows=[
                RowValidationResult(
                    row_number=1,
                    status="valid",
                    errors=[],
                    preview={"department_type": "it", "name": "IT"},
                ),
            ],
        )
    )
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", Mock()
        ) or setattr(self, "import_service", fake_import),
    )
    app = build_app(monkeypatch, user)

    from io import BytesIO

    csv_content = b"department_type,name\nit,IT\n"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/onboarding/imports/departments/validate",
            files={"upload": ("dept.csv", BytesIO(csv_content), "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    assert data["valid_rows"] == 1
    assert data["can_confirm"] is True


def test_confirm_import_completes_and_returns_result(monkeypatch) -> None:
    user = company_user()
    job_id = uuid4()
    fake_import = Mock()
    fake_import.confirm_import = AsyncMock(
        return_value=ImportConfirmResponse(
            import_job_id=job_id,
            status=ImportJobStatus.COMPLETED,
            processed_rows=2,
            errors=None,
        )
    )
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", Mock()
        ) or setattr(self, "import_service", fake_import),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/onboarding/imports/{job_id}/confirm")

    assert response.status_code == 200
    assert response.json()["processed_rows"] == 2
    assert response.json()["status"] == "completed"


def test_list_import_jobs_returns_jobs(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list_jobs = AsyncMock(return_value=[])
    fake_import = Mock()
    fake_import.job_repo = fake_repo
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", Mock()
        ) or setattr(self, "import_service", fake_import),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/onboarding/imports?limit=20")

    assert response.status_code == 200
    assert response.json() == []


def test_get_import_job_by_id(monkeypatch) -> None:
    user = company_user()
    job_id = uuid4()
    job = SimpleNamespace(
        id=job_id,
        company_id=user.company_id,
        import_type=ImportType.EMPLOYEES,
        status=ImportJobStatus.READY,
        original_filename="emp.csv",
        uploaded_by_user_id=user.user_id,
        total_rows=5,
        valid_rows=5,
        invalid_rows=0,
        processed_rows=0,
        error_summary=None,
        checksum="abc",
        idempotency_key="abc",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=None,
        completed_at=None,
        failed_at=None,
    )
    fake_repo = Mock()
    fake_repo.get_by_id = AsyncMock(return_value=job)
    fake_import = Mock()
    fake_import.job_repo = fake_repo
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", Mock()
        ) or setattr(self, "import_service", fake_import),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/onboarding/imports/{job_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_get_import_job_not_found(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.get_by_id = AsyncMock(return_value=None)
    fake_import = Mock()
    fake_import.job_repo = fake_repo
    monkeypatch.setattr(
        OnboardingService,
        "__init__",
        lambda self, session, company_id: setattr(
            self, "status_service", Mock()
        ) or setattr(self, "import_service", fake_import),
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/onboarding/imports/{uuid4()}")

    assert response.status_code == 404


def test_template_endpoint_returns_columns(monkeypatch) -> None:
    user = company_user()
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/onboarding/templates/employees")

    assert response.status_code == 200
    data = response.json()
    assert data["csv_header"]
    assert isinstance(data["columns"], list)
