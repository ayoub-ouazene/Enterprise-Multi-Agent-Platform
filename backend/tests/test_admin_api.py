"""Admin API router tests."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.admin.schemas import (
    AdminAssetResponse,
    AdminBudgetResponse,
    AdminDepartmentResponse,
    AdminEmployeeResponse,
    AdminHolidayResponse,
    AdminLeaveBalanceResponse,
    AdminPolicyReadinessResponse,
    AdminSoftwareCatalogResponse,
    AdminStaffingRuleResponse,
    AdminSupplierResponse,
)
from app.admin.service import (
    AdminAssetService,
    AdminBudgetService,
    AdminDepartmentService,
    AdminEmployeeService,
    AdminHolidayService,
    AdminLeaveBalanceService,
    AdminSoftwareCatalogService,
    AdminStaffingRuleService,
    AdminSupplierService,
)
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.database.session import get_db_session


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


def it_manager() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="it@example.com",
        actor_type=ActorType.DEPARTMENT_MANAGER,
        employee_id=uuid4(),
        department_id=uuid4(),
        is_manager=True,
    )


def build_app(monkeypatch, user) -> TestClient:
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(
        main_module, "create_database_engine", lambda _settings: engine
    )
    monkeypatch.setattr(
        main_module, "create_session_factory", lambda _engine: Mock()
    )
    app = main_module.create_app(build_settings())

    async def session_override():
        mock = AsyncMock()
        mock.scalar = AsyncMock(return_value=0)
        mock_scalars_result = Mock()
        mock_scalars_result.all = Mock(return_value=[])
        mock.scalars = AsyncMock(return_value=mock_scalars_result)
        yield mock

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return app


def _fake_dept(department_type: DepartmentType = DepartmentType.IT):
    d = Mock()
    d.id = uuid4()
    d.company_id = uuid4()
    d.name = "Test Department"
    d.department_type = department_type
    d.is_active = True
    d.custom_data = {}
    d.created_at = Mock()
    d.updated_at = Mock()
    return d


def _patch_dept_repo(monkeypatch, dept_type: DepartmentType):
    async def fake_get(*_a, **_k):
        return _fake_dept(dept_type)

    from app.departments.repository import DepartmentRepository

    monkeypatch.setattr(DepartmentRepository, "get_by_id", fake_get)


# ---------------------------------------------------------------------------
# Employee Directory
# ---------------------------------------------------------------------------


def test_list_employees_returns_records(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminEmployeeService, "__init__", lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/employees")

    assert response.status_code == 200
    assert response.json() == []


def test_create_employee_requires_company(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.IT)
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post("/api/v1/admin/employees", json={})

    assert response.status_code == 403


def test_get_employee_not_found(monkeypatch) -> None:
    user = company_user()
    from app.core.exceptions import NotFoundError

    fake_service = Mock()
    fake_service.get = AsyncMock(side_effect=NotFoundError("Employee not found"))
    monkeypatch.setattr(
        AdminEmployeeService, "__init__", lambda self, s, c: None
    )
    monkeypatch.setattr(
        AdminEmployeeService, "get", fake_service.get
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/admin/employees/{uuid4()}")

    assert response.status_code == 404


def test_delete_employee_requires_company(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.IT)
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/admin/employees/{uuid4()}")

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Department Configuration
# ---------------------------------------------------------------------------


def test_list_departments(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminDepartmentService, "__init__", lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/departments")

    assert response.status_code == 200
    assert response.json() == []


def test_update_department_requires_company(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.IT)
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.patch(f"/api/v1/admin/departments/{uuid4()}", json={})

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Asset Inventory
# ---------------------------------------------------------------------------


def test_list_assets(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminAssetService, "__init__", lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/assets")

    assert response.status_code == 200
    assert response.json() == []


def _fake_asset():
    from types import SimpleNamespace
    return SimpleNamespace(
        id=uuid4(),
        asset_code="LAP001",
        asset_type="laptop",
        brand="Dell",
        model="XPS 15",
        serial_number=None,
        status="available",
        location=None,
        custom_data={},
        version=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_create_asset_requires_it_admin(monkeypatch) -> None:
    user = company_user()
    fake_service = Mock()
    fake_service.create = AsyncMock(return_value=_fake_asset())
    monkeypatch.setattr(
        AdminAssetService, "__init__", lambda self, s, c: None
    )
    monkeypatch.setattr(AdminAssetService, "create", fake_service.create)
    app = build_app(monkeypatch, user)

    payload = {
        "asset_code": "LAP001",
        "asset_type": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/assets", json=payload)

    assert response.status_code == 201


def test_create_asset_denied_for_wrong_manager(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.HR)
    app = build_app(monkeypatch, user)

    payload = {
        "asset_code": "LAP001",
        "asset_type": "laptop",
        "brand": "Dell",
        "model": "XPS 15",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/assets", json=payload)

    assert response.status_code == 403


def test_update_asset_optimistic_lock(monkeypatch) -> None:
    user = company_user()
    from app.admin.service import OptimisticLockError

    fake_service = Mock()
    fake_service.update = AsyncMock(
        side_effect=OptimisticLockError("Asset was modified")
    )
    monkeypatch.setattr(
        AdminAssetService, "__init__", lambda self, s, c: None
    )
    monkeypatch.setattr(AdminAssetService, "update", fake_service.update)
    app = build_app(monkeypatch, user)

    payload = {"location": "Office", "version": 2}
    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/admin/assets/{uuid4()}", json=payload
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Software Catalog
# ---------------------------------------------------------------------------


def test_list_software_catalog(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminSoftwareCatalogService, "__init__",
        lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/software-catalog")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Budget Management
# ---------------------------------------------------------------------------


def _fake_budget():
    from types import SimpleNamespace
    return SimpleNamespace(
        id=uuid4(),
        department_id=None,
        name="Q1 Marketing",
        budget_type="department",
        currency="USD",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        allocated_amount=Decimal("50000.00"),
        reserved_amount=Decimal("0.00"),
        committed_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
        available_amount=Decimal("50000.00"),
        status="draft",
        approval_threshold=None,
        custom_data={},
        version=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_create_budget_requires_finance_admin(monkeypatch) -> None:
    user = company_user()
    fake_service = Mock()
    fake_service.create = AsyncMock(return_value=_fake_budget())
    monkeypatch.setattr(
        AdminBudgetService, "__init__", lambda self, s, c: None
    )
    monkeypatch.setattr(AdminBudgetService, "create", fake_service.create)
    app = build_app(monkeypatch, user)

    payload = {
        "name": "Q1 Marketing",
        "budget_type": "department",
        "currency": "USD",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "allocated_amount": "50000.00",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/budgets", json=payload)

    assert response.status_code == 201


def test_create_budget_denied_for_hr_manager(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.HR)
    app = build_app(monkeypatch, user)

    payload = {
        "name": "Q1",
        "budget_type": "department",
        "currency": "USD",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "allocated_amount": "50000.00",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/budgets", json=payload)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Leave Balances
# ---------------------------------------------------------------------------


def test_list_leave_balances(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list_for_employee = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminLeaveBalanceService, "__init__",
        lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/admin/employees/{uuid4()}/leave-balances"
        )

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------


def test_list_holidays(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminHolidayService, "__init__",
        lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/holidays")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Staffing Rules
# ---------------------------------------------------------------------------


def test_list_staffing_rules(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminStaffingRuleService, "__init__",
        lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/staffing-rules")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Supplier Directory
# ---------------------------------------------------------------------------


def test_list_suppliers(monkeypatch) -> None:
    user = company_user()
    fake_repo = Mock()
    fake_repo.list = AsyncMock(return_value=[])
    monkeypatch.setattr(
        AdminSupplierService, "__init__",
        lambda self, s, c: setattr(self, "repo", fake_repo)
    )
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/suppliers")

    assert response.status_code == 200
    assert response.json() == []


def _fake_supplier():
    from types import SimpleNamespace
    return SimpleNamespace(
        id=uuid4(),
        name="Acme Supplies",
        contact_person=None,
        email="contact@acme.example",
        phone=None,
        address=None,
        website=None,
        is_active=True,
        custom_data={},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def test_create_supplier_requires_procurement_admin(monkeypatch) -> None:
    user = company_user()
    fake_service = Mock()
    fake_service.create = AsyncMock(return_value=_fake_supplier())
    monkeypatch.setattr(
        AdminSupplierService, "__init__", lambda self, s, c: None
    )
    monkeypatch.setattr(AdminSupplierService, "create", fake_service.create)
    app = build_app(monkeypatch, user)

    payload = {
        "name": "Acme Supplies",
        "email": "contact@acme.example",
        "is_active": True,
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/suppliers", json=payload)

    assert response.status_code == 201


def test_create_supplier_denied_for_it_manager(monkeypatch) -> None:
    user = it_manager()
    _patch_dept_repo(monkeypatch, DepartmentType.IT)
    app = build_app(monkeypatch, user)

    payload = {"name": "Acme Supplies", "email": "contact@acme.example"}
    with TestClient(app) as client:
        response = client.post("/api/v1/admin/suppliers", json=payload)

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Policy Readiness
# ---------------------------------------------------------------------------


def test_policy_readiness_empty(monkeypatch) -> None:
    user = company_user()
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/policy-readiness")

    assert response.status_code == 200
    data = response.json()
    assert data["total_documents"] == 0
    assert data["ready"] is False


# ---------------------------------------------------------------------------
# Onboarding Status
# ---------------------------------------------------------------------------


def test_admin_onboarding_status(monkeypatch) -> None:
    user = company_user()
    app = build_app(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/admin/onboarding-status")

    assert response.status_code == 200
    data = response.json()
    assert "company_id" in data
    assert "is_active" in data
