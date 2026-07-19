from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.departments.finance.router as router_module
import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.database.session import get_db_session


def settings() -> Settings:
    return Settings(
        _env_file=None, app_env="test", debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def user(actor: ActorType, *, department_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(), company_id=uuid4(), email="user@example.com", actor_type=actor,
        employee_id=uuid4() if department_id else None, department_id=department_id,
        is_manager=actor == ActorType.DEPARTMENT_MANAGER,
    )


def app(monkeypatch, current):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    application = main_module.create_app(settings())

    async def session_override():
        yield AsyncMock()

    application.dependency_overrides[get_db_session] = session_override
    application.dependency_overrides[require_authenticated_user] = lambda: current
    return application


def budget_record(department_id=None):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(), department_id=department_id, name="Operations", budget_type="operational",
        currency="USD", period_start=date(2026, 1, 1), period_end=date(2026, 12, 31),
        allocated_amount=Decimal("1000.00"), reserved_amount=Decimal("100.00"),
        committed_amount=Decimal("200.00"), spent_amount=Decimal("300.00"),
        available_amount=Decimal("400.00"), status="active",
        approval_threshold=Decimal("500.00"), created_at=now, updated_at=now,
    )


def transaction_record():
    return SimpleNamespace(
        id=uuid4(), request_id=uuid4(), budget_id=uuid4(), transaction_type="reservation",
        amount=Decimal("50.00"), currency="USD", status="confirmed",
        description="Authorized reservation", reference="finance:req:reservation",
        confirmed_at=datetime.now(UTC), reversed_transaction_id=None,
        created_at=datetime.now(UTC),
    )


def test_company_account_can_list_transactions(monkeypatch) -> None:
    current = user(ActorType.COMPANY)
    repository = Mock()
    repository.list = AsyncMock(return_value=[transaction_record()])
    monkeypatch.setattr(router_module, "FinancialTransactionRepository", lambda *_: repository)
    with TestClient(app(monkeypatch, current)) as client:
        response = client.get("/api/v1/financial-transactions")
    assert response.status_code == 200
    assert response.json()[0]["status"] == "confirmed"
    assert "custom_data" not in response.json()[0]


def test_normal_employee_cannot_list_financial_records(monkeypatch) -> None:
    with TestClient(app(monkeypatch, user(ActorType.EMPLOYEE))) as client:
        response = client.get("/api/v1/financial-transactions")
    assert response.status_code == 403


def test_department_manager_sees_only_own_budget_summary(monkeypatch) -> None:
    department_id = uuid4()
    current = user(ActorType.DEPARTMENT_MANAGER, department_id=department_id)
    budgets = Mock()
    budgets.list = AsyncMock(return_value=[budget_record(department_id)])
    departments = Mock()
    departments.get_by_id = AsyncMock(return_value=SimpleNamespace(
        id=department_id, is_active=True, department_type=DepartmentType.IT,
    ))
    monkeypatch.setattr(router_module, "BudgetRepository", lambda *_: budgets)
    monkeypatch.setattr(router_module, "DepartmentRepository", lambda *_: departments)
    with TestClient(app(monkeypatch, current)) as client:
        response = client.get("/api/v1/budgets")
    assert response.status_code == 200
    budgets.list.assert_awaited_once_with(department_id=department_id, limit=100, offset=0)
