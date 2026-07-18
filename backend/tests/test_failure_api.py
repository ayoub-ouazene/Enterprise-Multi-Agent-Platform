from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.failures.router as router_module
import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.failures.enums import CapabilityGapStatus, FailureSource, FailureType


def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def user(actor, department_id=None):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="user@example.com",
        actor_type=actor,
        employee_id=uuid4() if department_id else None,
        department_id=department_id,
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


def failure():
    return SimpleNamespace(
        id=uuid4(),
        request_id=None,
        department_id=None,
        failure_type=FailureType.DATABASE_FAILURE,
        failure_source=FailureSource.REPOSITORY,
        failed_operation="read_inventory",
        internal_message="sanitized",
        safe_message="Safe message",
        error_code=None,
        technical_data={},
        alternative_attempted=False,
        alternative_description=None,
        is_terminal=False,
        resolved=False,
        resolved_at=None,
        resolved_by_user_id=None,
        created_at=datetime.now(UTC),
    )


def gap():
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        request_id=None,
        department_id=None,
        requested_operation="Export records",
        description="Unsupported",
        safe_user_message="Not supported",
        status=CapabilityGapStatus.OPEN,
        occurrence_count=1,
        first_seen_at=now,
        last_seen_at=now,
        resolved_at=None,
        resolved_by_user_id=None,
        resolution_notes=None,
        created_at=now,
        updated_at=now,
    )


def test_company_lists_failures(monkeypatch) -> None:
    current = user(ActorType.COMPANY)
    service = Mock()
    service.list = AsyncMock(return_value=[failure()])
    monkeypatch.setattr(router_module, "_failure_service", lambda *_: service)
    with TestClient(app(monkeypatch, current)) as client:
        response = client.get("/api/v1/failures")
    assert response.status_code == 200
    assert "safe_message" in response.json()[0]


def test_employee_cannot_access_internal_failures(monkeypatch) -> None:
    with TestClient(app(monkeypatch, user(ActorType.EMPLOYEE))) as client:
        response = client.get("/api/v1/failures")
    assert response.status_code == 403


def test_cross_company_failure_is_not_found(monkeypatch) -> None:
    current = user(ActorType.COMPANY)
    service = Mock()
    service.get = AsyncMock(side_effect=NotFoundError())
    monkeypatch.setattr(router_module, "_failure_service", lambda *_: service)
    with TestClient(app(monkeypatch, current)) as client:
        response = client.get(f"/api/v1/failures/{uuid4()}")
    assert response.status_code == 404


def test_company_updates_capability_gap_status(monkeypatch) -> None:
    current = user(ActorType.COMPANY)
    record = gap()
    record.status = CapabilityGapStatus.PLANNED
    service = Mock()
    service.update_status = AsyncMock(return_value=record)
    monkeypatch.setattr(router_module, "_gap_service", lambda *_: service)
    with TestClient(app(monkeypatch, current)) as client:
        response = client.post(
            f"/api/v1/capability-gaps/{record.id}/status", json={"status": "planned"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "planned"


def test_manager_cannot_update_gap_status(monkeypatch) -> None:
    current = user(ActorType.DEPARTMENT_MANAGER, uuid4())
    with TestClient(app(monkeypatch, current)) as client:
        response = client.post(
            f"/api/v1/capability-gaps/{uuid4()}/status", json={"status": "planned"}
        )
    assert response.status_code == 403
