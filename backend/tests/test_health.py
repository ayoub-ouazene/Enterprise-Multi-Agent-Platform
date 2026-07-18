from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import Settings
from app.database.health import get_database_health


def build_test_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test?ssl=require",
        alembic_database_url=(
            "postgresql+asyncpg://test:test@localhost/test?ssl=require"
        ),
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


async def database_is_healthy() -> bool:
    return True


async def database_is_unavailable() -> bool:
    return False


def test_health_reports_application_and_database_health(monkeypatch) -> None:
    engine = Mock()
    engine.dispose = AsyncMock()
    session_factory = Mock()

    monkeypatch.setattr(main_module, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        lambda created_engine: session_factory,
    )

    application = main_module.create_app(build_test_settings())
    application.dependency_overrides[get_database_health] = database_is_healthy

    with TestClient(application) as client:
        response = client.get("/health")

        assert application.state.engine is engine
        assert application.state.session_factory is session_factory

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "application": "ok",
        "database": "ok",
    }
    engine.dispose.assert_awaited_once()


def test_health_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    engine = Mock()
    engine.dispose = AsyncMock()

    monkeypatch.setattr(main_module, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda engine: Mock())

    application = main_module.create_app(build_test_settings())
    application.dependency_overrides[get_database_health] = database_is_unavailable

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "application": "ok",
        "database": "unavailable",
    }
