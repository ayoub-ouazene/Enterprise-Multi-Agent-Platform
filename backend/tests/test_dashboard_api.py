from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.dashboard.schemas import DashboardIdentity, DashboardResponse
from app.dashboard.service import DashboardService
from app.database.session import get_db_session


def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def test_dashboard_returns_bounded_safe_projection(monkeypatch):
    user = AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="employee@example.com",
        actor_type=ActorType.EMPLOYEE,
    )
    response = DashboardResponse(
        role="employee",
        identity=DashboardIdentity(
            company_name="Example Company",
            company_active=True,
            account_label="Employee",
        ),
        metrics=[],
        attention=[],
        active_requests=[],
        completed_requests=[],
        pending_actions=[],
        activity=[],
        generated_at=datetime.now(UTC),
    )
    monkeypatch.setattr(DashboardService, "get", AsyncMock(return_value=response))
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    app = main_module.create_app(settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: user
    with TestClient(app) as client:
        result = client.get("/api/v1/dashboard")
    assert result.status_code == 200
    payload = result.json()
    assert payload["role"] == "employee"
    assert "workflow_state" not in str(payload)
    assert "decision_package" not in str(payload)
    assert "password_hash" not in str(payload)
