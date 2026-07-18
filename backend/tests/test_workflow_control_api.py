from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.workflow.router as workflow_router_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.requests.enums import RequestStatus
from app.workflow.exceptions import (
    WorkflowAlreadyStartedError,
    WorkflowExecutionFailedError,
    WorkflowPermissionError,
    WorkflowPersistenceError,
)
from app.workflow.schemas import WorkflowControlResponse


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
        email="company@example.com",
        actor_type=ActorType.COMPANY,
    )


def build_application(monkeypatch, current_user):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        lambda created_engine: Mock(),
    )
    application = main_module.create_app(build_settings())

    async def session_override():
        yield AsyncMock()

    application.dependency_overrides[get_db_session] = session_override
    application.dependency_overrides[require_authenticated_user] = lambda: current_user
    return application


def response(request_id=None) -> WorkflowControlResponse:
    department_id = uuid4()
    return WorkflowControlResponse(
        request_id=request_id or uuid4(),
        status=RequestStatus.COMPLETED,
        current_stage="completed",
        owner_department_id=department_id,
        active_department_id=department_id,
        state_version=1,
    )


def test_start_endpoint_returns_safe_control_response(monkeypatch) -> None:
    current = company_user()
    request_id = uuid4()
    fake_service = Mock()
    fake_service.start = AsyncMock(return_value=response(request_id))
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{request_id}/workflow/start")

    assert result.status_code == 200
    assert result.json()["request_id"] == str(request_id)
    assert result.json()["status"] == "completed"
    assert "workflow_state" not in result.text
    fake_service.start.assert_awaited_once_with(request_id)


def test_resume_endpoint_calls_resume_service(monkeypatch) -> None:
    current = company_user()
    request_id = uuid4()
    fake_service = Mock()
    fake_service.resume = AsyncMock(return_value=response(request_id))
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{request_id}/workflow/resume")

    assert result.status_code == 200
    fake_service.resume.assert_awaited_once_with(request_id)


def test_cross_company_control_returns_not_found(monkeypatch) -> None:
    current = company_user()
    fake_service = Mock()
    fake_service.start = AsyncMock(side_effect=NotFoundError())
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{uuid4()}/workflow/start")

    assert result.status_code == 404
    assert result.json() == {"detail": "Business request not found"}


def test_unauthorized_workflow_control_returns_forbidden(monkeypatch) -> None:
    current = company_user()
    fake_service = Mock()
    fake_service.start = AsyncMock(side_effect=WorkflowPermissionError())
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{uuid4()}/workflow/start")

    assert result.status_code == 403
    assert result.json() == {"detail": "Insufficient permissions"}


def test_duplicate_start_returns_conflict(monkeypatch) -> None:
    current = company_user()
    fake_service = Mock()
    fake_service.start = AsyncMock(
        side_effect=WorkflowAlreadyStartedError("Workflow has already started")
    )
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{uuid4()}/workflow/start")

    assert result.status_code == 409
    assert result.json() == {"detail": "Workflow has already started"}


def test_graph_error_does_not_expose_internal_exception(monkeypatch) -> None:
    current = company_user()
    fake_service = Mock()
    fake_service.start = AsyncMock(side_effect=WorkflowExecutionFailedError("secret"))
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{uuid4()}/workflow/start")

    assert result.status_code == 500
    assert result.json() == {"detail": "Workflow execution failed"}
    assert "secret" not in result.text


def test_persistence_error_returns_generic_unavailable_response(monkeypatch) -> None:
    current = company_user()
    fake_service = Mock()
    fake_service.start = AsyncMock(side_effect=WorkflowPersistenceError("db detail"))
    monkeypatch.setattr(
        workflow_router_module,
        "_service",
        lambda session, user, settings: fake_service,
    )
    application = build_application(monkeypatch, current)

    with TestClient(application) as client:
        result = client.post(f"/api/v1/requests/{uuid4()}/workflow/start")

    assert result.status_code == 503
    assert result.json() == {"detail": "Workflow persistence is unavailable"}
    assert "db detail" not in result.text
