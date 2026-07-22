"""Onboarding service unit tests."""
import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType, EmploymentStatus
from app.core.exceptions import (
    BusinessValidationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.onboarding.enums import ImportJobStatus, ImportType
from app.onboarding.models import ImportJob
from app.onboarding.parser import ParsedUpload
from app.onboarding.service import (
    CompanyOnboardingService,
    OnboardingImportService,
)


def company_onboarding_service(company_id, session=None):
    session = session or AsyncMock(spec=AsyncSession)
    return CompanyOnboardingService(session, company_id)


def import_service(company_id, session=None):
    session = session or AsyncMock(spec=AsyncSession)
    return OnboardingImportService(session, company_id)


def mock_company(**kwargs):
    defaults = {
        "id": uuid4(),
        "name": "TestCo",
        "slug": "testco",
        "is_active": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# CompanyOnboardingService
# ---------------------------------------------------------------------------

def test_get_status_raises_not_found_when_company_missing() -> None:
    svc = company_onboarding_service(uuid4())
    svc.session.scalar = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError, match="Company not found"):
        asyncio.run(svc.get_status())


def test_activate_rejects_non_company_account() -> None:
    company_id = uuid4()
    svc = company_onboarding_service(company_id)
    user = AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id,
        email="emp@example.com",
        actor_type=ActorType.EMPLOYEE,
        employee_id=uuid4(),
    )

    with pytest.raises(ForbiddenError, match="Only company accounts"):
        asyncio.run(svc.activate(user))


def test_activate_rejects_already_active(monkeypatch) -> None:
    from app.onboarding.schemas import OnboardingStatusResponse

    company_id = uuid4()
    svc = company_onboarding_service(company_id)
    monkeypatch.setattr(
        CompanyOnboardingService,
        "get_status",
        AsyncMock(
            return_value=OnboardingStatusResponse(
                company_id=company_id,
                can_activate=False,
                is_active=True,
                items=[],
            )
        ),
    )
    user = AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id,
        email="admin@example.com",
        actor_type=ActorType.COMPANY,
    )

    with pytest.raises(BusinessValidationError, match="already active"):
        asyncio.run(svc.activate(user))


# ---------------------------------------------------------------------------
# OnboardingImportService
# ---------------------------------------------------------------------------

def test_validate_import_raises_on_missing_columns() -> None:
    svc = import_service(uuid4())
    parsed = ParsedUpload(
        headers=["email"],
        rows=[{"email": "a@example.com"}],
        checksum="sum",
        original_filename="bad.csv",
    )
    with pytest.raises(BusinessValidationError, match="Missing required"):
        asyncio.run(
            svc.validate_import(
                ImportType.EMPLOYEES,
                parsed,
                uuid4(),
            )
        )


def test_validate_import_detects_duplicate_checksum() -> None:
    company_id = uuid4()
    svc = import_service(company_id)
    existing = Mock(spec=ImportJob)
    svc.job_repo = Mock()
    svc.job_repo.find_existing_completed = AsyncMock(return_value=existing)

    parsed = ParsedUpload(
        headers=["department_type", "name"],
        rows=[{"department_type": "it", "name": "IT"}],
        checksum="abc123",
        original_filename="dept.csv",
    )
    with pytest.raises(ConflictError, match="already completed"):
        asyncio.run(
            svc.validate_import(
                ImportType.DEPARTMENTS,
                parsed,
                uuid4(),
            )
        )


def test_validate_import_creates_job_and_returns_response() -> None:
    company_id = uuid4()
    svc = import_service(company_id)
    job = Mock(spec=ImportJob)
    job.id = uuid4()
    job.status = ImportJobStatus.READY
    svc.job_repo = Mock()
    svc.job_repo.find_existing_completed = AsyncMock(return_value=None)
    svc.job_repo.create = AsyncMock(return_value=job)
    svc.job_repo.update_status = AsyncMock(return_value=job)

    parsed = ParsedUpload(
        headers=["department_type", "name"],
        rows=[
            {"department_type": "it", "name": "IT"},
            {"department_type": "hr", "name": "HR"},
        ],
        checksum="abc",
        original_filename="dept.csv",
    )
    svc.session.commit = AsyncMock()
    svc.session.refresh = AsyncMock()
    svc.session.scalars = AsyncMock(return_value=Mock(all=Mock(return_value=[])))

    result = asyncio.run(
        svc.validate_import(
            ImportType.DEPARTMENTS,
            parsed,
            uuid4(),
        )
    )
    assert result.import_job_id == job.id
    assert result.total_rows == 2
    assert result.valid_rows == 2
    assert result.can_confirm is True


def test_confirm_import_rejects_non_company() -> None:
    svc = import_service(uuid4())
    user = AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="emp@example.com",
        actor_type=ActorType.EMPLOYEE,
    )
    with pytest.raises(ForbiddenError, match="Only company accounts"):
        asyncio.run(svc.confirm_import(uuid4(), user))


def test_validate_employee_password_errors_propagate() -> None:
    company_id = uuid4()
    svc = import_service(company_id)
    rows = [
        {
            "email": "a@example.com",
            "first_name": "A",
            "last_name": "B",
            "temporary_password": "short",
            "employee_code": "E001",
            "department": "it",
            "job_title": "Dev",
            "employment_status": "active",
        }
    ]
    svc.session.scalars = AsyncMock(return_value=Mock(all=Mock(return_value=[])))

    results, valid, invalid = asyncio.run(svc._validate_employee_rows(rows))
    assert invalid > 0
    assert any("Password" in " ".join(r.errors) for r in results)


def test_validate_department_rows_detects_duplicate_type() -> None:
    company_id = uuid4()
    svc = import_service(company_id)
    svc.session.scalars = AsyncMock(return_value=Mock(all=Mock(return_value=[])))
    rows = [
        {"department_type": "invalid", "name": "X"},
        {"department_type": "it", "name": "IT"},
    ]
    results, valid, invalid = asyncio.run(svc._validate_department_rows(rows))
    assert invalid >= 1
    assert any("invalid" in " ".join(r.errors).lower() for r in results)


def test_template_columns_match_required() -> None:
    from app.onboarding.parser import REQUIRED_EMPLOYEE_COLUMNS, REQUIRED_DEPARTMENT_COLUMNS
    from app.onboarding.parser import get_template_columns

    emp_cols = get_template_columns("employees")
    required_names = {c["name"] for c in emp_cols if c["required"]}
    assert required_names == REQUIRED_EMPLOYEE_COLUMNS

    dept_cols = get_template_columns("departments")
    required_names = {c["name"] for c in dept_cols if c["required"]}
    assert required_names == REQUIRED_DEPARTMENT_COLUMNS
