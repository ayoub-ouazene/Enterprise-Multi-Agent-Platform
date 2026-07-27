from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.database.session import get_db_session
from app.human_actions.schemas import (
    HumanActionDetailResponse,
    HumanActionSubmitResponse,
    HumanActionSummaryResponse,
    RelatedRequestSummary,
)
from app.human_actions.service import HumanActionPermissionError
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


def company_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="company@example.com",
        actor_type=ActorType.COMPANY,
        employee_id=uuid4(),
    )


def employee_user(company_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="employee@example.com",
        actor_type=ActorType.EMPLOYEE,
        employee_id=uuid4(),
    )


def manager_user(company_id=None) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="manager@example.com",
        actor_type=ActorType.DEPARTMENT_MANAGER,
        employee_id=uuid4(),
    )


def action_record(user: AuthenticatedUser, **overrides):
    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "company_id": user.company_id,
        "request_id": uuid4(),
        "action_type": "approval",
        "title": "Approve budget",
        "description": "Budget approval needed.",
        "status": "pending",
        "assigned_user_id": user.user_id,
        "assigned_role": None,
        "decision_package": {"amount": 1000},
        "response": {},
        "due_date": None,
        "resolved_at": None,
        "created_at": now,
        "updated_at": now,
        "request": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def safe_summary(record):
    return HumanActionSummaryResponse(
        id=record.id, request_id=record.request_id, action_type=record.action_type,
        title=record.title, status=record.status, assigned_role=record.assigned_role,
        due_date=record.due_date, resolved_at=record.resolved_at,
        created_at=record.created_at, updated_at=record.updated_at,
        allowed_decisions=["approved", "rejected"], can_respond=True,
        request_title="Test request", request_status="processing",
        requesting_department="Finance",
    )


def safe_detail(record):
    return HumanActionDetailResponse(
        **safe_summary(record).model_dump(), description=record.description,
        safe_context={"amount": "1000.00", "currency": "USD"},
        related_request=RelatedRequestSummary(
            id=record.request_id, title="Test request", status="processing",
            owner_department="Finance",
        ),
    )


def build_application(monkeypatch, user: AuthenticatedUser):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda settings: engine)
    monkeypatch.setattr(
        main_module, "create_session_factory", lambda created_engine: Mock()
    )
    app = main_module.create_app(build_settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: user
    return app


# --- List ---


def test_list_actions_requires_authentication(monkeypatch) -> None:
    app = build_application(monkeypatch, company_user())
    del app.dependency_overrides[require_authenticated_user]

    with TestClient(app) as client:
        response = client.get("/api/v1/human-actions")

    assert response.status_code == 401


def test_list_actions_returns_actions(monkeypatch) -> None:
    user = company_user()
    record = action_record(user)
    fake_service = Mock()
    fake_service.list_public = AsyncMock(return_value=[safe_summary(record)])

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get("/api/v1/human-actions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Approve budget"
    assert body[0]["status"] == "pending"


# --- Get ---


def test_get_action_not_found(monkeypatch) -> None:
    user = company_user()
    fake_service = Mock()
    fake_service.get_public = AsyncMock(side_effect=NotFoundError("Not found"))

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/human-actions/{uuid4()}")

    assert response.status_code == 404


# --- Create ---


def test_create_action_rejects_unauthorized_user(monkeypatch) -> None:
    user = employee_user()
    fake_service = Mock()
    fake_service.create = AsyncMock(side_effect=HumanActionPermissionError("No permission"))

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/human-actions",
            json={
                "request_id": str(uuid4()),
                "action_type": "approval",
                "title": "Approve budget",
                "description": "Budget approval needed.",
            },
        )

    assert response.status_code == 403


def test_create_action_validates_schema(monkeypatch) -> None:
    user = company_user()
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/human-actions",
            json={
                "request_id": str(uuid4()),
                "action_type": "",
                "title": "Approve budget",
                "description": "Budget approval needed.",
            },
        )

    assert response.status_code == 422


def test_get_action_returns_action(monkeypatch) -> None:
    user = company_user()
    record = action_record(user)
    fake_service = Mock()
    fake_service.get_public = AsyncMock(return_value=safe_detail(record))

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/human-actions/{record.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(record.id)
    assert body["title"] == "Approve budget"
    assert body["safe_context"] == {"amount": "1000.00", "currency": "USD"}
    assert "decision_package" not in body


# --- Submit ---


def test_submit_action_returns_resolved(monkeypatch) -> None:
    user = company_user()
    record = action_record(user, status="resolved")
    fake_service = Mock()
    fake_service.submit = AsyncMock(return_value=HumanActionSubmitResponse(
        id=record.id,
        status="resolved",
        resolved_at=datetime.now(UTC),
    ))

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/human-actions/{record.id}/submit",
            json={"decision": "approved", "response": "Looks good."},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None


def test_submit_action_rejects_double_submit(monkeypatch) -> None:
    user = company_user()
    record = action_record(user)
    fake_service = Mock()
    fake_service.submit = AsyncMock(side_effect=BusinessValidationError("Already resolved"))

    import app.human_actions.router as human_actions_router_module

    monkeypatch.setattr(
        human_actions_router_module,
        "_service",
        lambda session, authenticated_user: fake_service,
    )
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/human-actions/{record.id}/submit",
            json={"decision": "approved", "response": "Looks good."},
        )

    assert response.status_code == 409


def test_submit_action_validates_empty_decision(monkeypatch) -> None:
    user = company_user()
    app = build_application(monkeypatch, user)

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/human-actions/{uuid4()}/submit",
            json={"decision": "", "response": "Looks good."},
        )

    assert response.status_code == 422


# --- Computed fields in response ---


def test_get_action_includes_computed_fields(monkeypatch) -> None:
    """GET action should include allowed_decisions, can_respond, request_title, request_status."""
    from app.human_actions.service import HumanActionService
    from app.human_actions.schemas import HumanActionResponse

    user = company_user()
    request_obj = SimpleNamespace(
        id=uuid4(),
        title="Test Request",
        status=RequestStatus.PROCESSING,
    )
    record = action_record(user, action_type="supplier_selection", request=request_obj)

    service = HumanActionService(Mock(), user)
    response = service._to_response(record)

    assert isinstance(response, HumanActionResponse)
    assert response.allowed_decisions == ["selected", "rejected"]
    assert response.can_respond is True
    assert response.request_title == "Test Request"
    assert response.request_status == "processing"


def test_allowed_decisions_mapping(monkeypatch) -> None:
    from app.human_actions.service import HumanActionService

    assert HumanActionService._allowed_decisions_for("supplier_selection") == ["selected", "rejected"]
    assert HumanActionService._allowed_decisions_for("technician_action") == ["completed", "failed", "unable"]
    assert HumanActionService._allowed_decisions_for("information_request") == ["submitted", "unable"]
    assert HumanActionService._allowed_decisions_for("unknown_type") == ["approved", "rejected"]


def test_can_respond_logic(monkeypatch) -> None:
    from app.human_actions.service import HumanActionService

    user = company_user()
    service = HumanActionService(Mock(), user)

    pending_assigned = action_record(user, status="pending")
    assert service._can_respond(pending_assigned) is True

    resolved = action_record(user, status="resolved")
    assert service._can_respond(resolved) is False

    employee = employee_user(user.company_id)
    service_emp = HumanActionService(Mock(), employee)
    action_not_assigned = action_record(user, status="pending", assigned_user_id=uuid4())
    assert service_emp._can_respond(action_not_assigned) is False
