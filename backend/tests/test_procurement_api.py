from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session


def settings() -> Settings:
    return Settings(
        _env_file=None, app_env="test", debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def application(monkeypatch, actor: ActorType):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    app = main_module.create_app(settings())
    current = AuthenticatedUser(
        user_id=uuid4(), company_id=uuid4(), email="user@example.com",
        actor_type=actor, employee_id=uuid4() if actor == ActorType.EMPLOYEE else None,
    )

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: current
    return app


def test_ordinary_employee_cannot_create_supplier_candidate(monkeypatch) -> None:
    app = application(monkeypatch, ActorType.EMPLOYEE)
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/procurement-requests/{uuid4()}/candidates",
            json={
                "supplier_name": "Supplier A", "item_or_service": "Laptop",
                "quoted_unit_price": "100.00", "quantity": "1.000",
                "currency": "USD", "source_type": "manual_entry",
            },
        )
    assert response.status_code == 403


def test_procurement_routes_do_not_expose_purchase_or_payment_endpoints(monkeypatch) -> None:
    app = application(monkeypatch, ActorType.COMPANY)
    paths = {route.path for route in app.routes}
    assert "/api/v1/procurement-requests/{request_id}" in paths
    assert "/api/v1/procurement-requests/{request_id}/candidates" in paths
    assert "/api/v1/supplier-candidates/{candidate_id}" in paths
    assert all("payment" not in path and "purchase-orders" not in path for path in paths)
