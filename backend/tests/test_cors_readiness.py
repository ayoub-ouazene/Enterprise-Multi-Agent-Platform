from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings
from app.database.health import get_database_health, get_database_readiness


def build_app(monkeypatch):
    settings = Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
        cors_origins=["http://localhost:5173"],
    )
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    app = main_module.create_app(settings)
    return app


def test_configured_frontend_origin_passes_cors_preflight(monkeypatch) -> None:
    app = build_app(monkeypatch)
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_readiness_reports_migration_required(monkeypatch) -> None:
    app = build_app(monkeypatch)
    app.dependency_overrides[get_database_health] = lambda: True
    app.dependency_overrides[get_database_readiness] = lambda: False

    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["database"] == "migration_required"
