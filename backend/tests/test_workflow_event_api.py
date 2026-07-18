from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.requests.router as request_router_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.workflow.enums import WorkflowEventType
from app.workflow.schemas import WorkflowEventPublicResponse


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


def build_application(monkeypatch, user=None):
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
    if user is not None:
        application.dependency_overrides[require_authenticated_user] = lambda: user
    return application


def public_event(request_id):
    return WorkflowEventPublicResponse(
        id=uuid4(),
        request_id=request_id,
        event_type=WorkflowEventType.REQUEST_CREATED,
        stage="request_received",
        title="Request created",
        message="The request has been created.",
        actor_label="Requester",
        department_id=None,
        event_data={},
        sequence_number=1,
        created_at=datetime.now(UTC),
    )


def test_timeline_endpoint_returns_only_public_fields(monkeypatch) -> None:
    user = current_user()
    request_id = uuid4()
    event = public_event(request_id)
    service = Mock()
    service.timeline = AsyncMock(return_value=[event])
    monkeypatch.setattr(
        request_router_module,
        "_workflow_event_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get(f"/api/v1/requests/{request_id}/events?limit=25&offset=0")

    assert response.status_code == 200
    assert response.json()[0]["sequence_number"] == 1
    assert "company_id" not in response.text
    assert "actor_user_id" not in response.text
    assert "visibility" not in response.text
    service.timeline.assert_awaited_once_with(
        request_id,
        event_type=None,
        limit=25,
        offset=0,
    )


def test_cross_company_timeline_returns_not_found(monkeypatch) -> None:
    user = current_user()
    service = Mock()
    service.timeline = AsyncMock(side_effect=NotFoundError("not found"))
    monkeypatch.setattr(
        request_router_module,
        "_workflow_event_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get(f"/api/v1/requests/{uuid4()}/events")

    assert response.status_code == 404
    assert response.json() == {"detail": "Business request not found"}


def test_timeline_requires_authentication(monkeypatch) -> None:
    application = build_application(monkeypatch)

    with TestClient(application) as client:
        response = client.get(f"/api/v1/requests/{uuid4()}/events")

    assert response.status_code == 401


def test_no_event_delete_endpoint_exists(monkeypatch) -> None:
    application = build_application(monkeypatch, current_user())

    with TestClient(application) as client:
        response = client.delete(f"/api/v1/requests/{uuid4()}/events/{uuid4()}")

    assert response.status_code in {404, 405}
