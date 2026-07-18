from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.requests.router as request_router_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session
from app.requests.enums import RequestPriority, RequestStatus


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def current_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="employee@example.com",
        actor_type=ActorType.EMPLOYEE,
        employee_id=uuid4(),
    )


def request_record(user: AuthenticatedUser):
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        company_id=user.company_id,
        requester_user_id=user.user_id,
        requester_employee_id=user.employee_id,
        owner_department_id=None,
        active_department_id=None,
        request_type="software_access",
        title="Access request",
        summary="Access is needed.",
        status=RequestStatus.CREATED,
        current_stage="request_received",
        priority=RequestPriority.NORMAL,
        workflow_state={"execution": {"api_key": "must-never-be-exposed"}},
        custom_data={"private": "internal"},
        final_decision=None,
        final_reason=None,
        created_at=now,
        updated_at=now,
        completed_at=None,
        cancelled_at=None,
        failed_at=None,
    )


def build_application(monkeypatch, user: AuthenticatedUser):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(
        main_module, "create_session_factory", lambda created_engine: Mock()
    )
    application = main_module.create_app(build_settings())

    async def session_override():
        yield AsyncMock()

    application.dependency_overrides[get_db_session] = session_override
    application.dependency_overrides[require_authenticated_user] = lambda: user
    return application


def test_create_endpoint_persists_only_client_allowed_input(monkeypatch) -> None:
    user = current_user()
    record = request_record(user)
    fake_service = Mock()
    fake_service.create = AsyncMock(return_value=record)
    monkeypatch.setattr(
        request_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/requests",
            json={
                "request_type": "software_access",
                "title": "Access request",
                "summary": "Access is needed.",
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["owner_department_id"] is None
    assert response.json()["requester_user_id"] == str(user.user_id)


def test_create_endpoint_rejects_client_company_and_requester_identity(
    monkeypatch,
) -> None:
    user = current_user()
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/requests",
            json={
                "request_type": "software_access",
                "title": "Access request",
                "summary": "Access is needed.",
                "company_id": str(uuid4()),
                "requester_user_id": str(uuid4()),
            },
        )

    assert response.status_code == 422


def test_request_detail_never_exposes_raw_workflow_state_or_custom_data(
    monkeypatch,
) -> None:
    user = current_user()
    record = request_record(user)
    fake_service = Mock()
    fake_service.get = AsyncMock(return_value=record)
    monkeypatch.setattr(
        request_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get(f"/api/v1/requests/{record.id}")

    assert response.status_code == 200
    assert "workflow_state" not in response.json()
    assert "custom_data" not in response.json()
    assert "api_key" not in response.text


def test_list_endpoint_returns_only_safe_summaries(monkeypatch) -> None:
    user = current_user()
    record = request_record(user)
    fake_service = Mock()
    fake_service.list = AsyncMock(return_value=[record])
    monkeypatch.setattr(
        request_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get("/api/v1/requests")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(record.id)
    assert "workflow_state" not in response.text
    assert "requester_user_id" not in response.text


def test_cancel_endpoint_returns_cancelled_request(monkeypatch) -> None:
    user = current_user()
    record = request_record(user)
    record.status = RequestStatus.CANCELLED
    record.current_stage = RequestStatus.CANCELLED.value
    record.cancelled_at = datetime.now(UTC)
    record.final_reason = "Cancelled by requester"
    fake_service = Mock()
    fake_service.cancel = AsyncMock(return_value=record)
    monkeypatch.setattr(
        request_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(f"/api/v1/requests/{record.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["final_reason"] == "Cancelled by requester"
