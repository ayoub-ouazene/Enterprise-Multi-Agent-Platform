from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.notifications.router as notification_router_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.notifications.enums import NotificationSeverity, NotificationType


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


def notification_record(user):
    return SimpleNamespace(
        id=uuid4(),
        company_id=user.company_id,
        recipient_user_id=user.user_id,
        request_id=uuid4(),
        notification_type=NotificationType.REQUEST_CREATED,
        title="Request created",
        message="Your request has been created.",
        severity=NotificationSeverity.INFO,
        action_required=False,
        action_type=None,
        action_url=None,
        notification_metadata={
            "password": "must-not-appear",
            "access_token": "must-not-appear",
        },
        is_read=False,
        read_at=None,
        created_at=datetime.now(UTC),
        expires_at=None,
    )


def build_application(monkeypatch, user):
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
    application.dependency_overrides[require_authenticated_user] = lambda: user
    return application


def test_list_returns_only_current_users_safe_notification_fields(monkeypatch) -> None:
    user = current_user()
    notification = notification_record(user)
    service = Mock()
    service.list_for_user = AsyncMock(return_value=[notification])
    monkeypatch.setattr(
        notification_router_module,
        "_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get("/api/v1/notifications?is_read=false&limit=25&offset=0")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(notification.id)
    assert "company_id" not in response.text
    assert "recipient_user_id" not in response.text
    assert "metadata" not in response.text
    assert "password" not in response.text
    assert "access_token" not in response.text
    assert service.list_for_user.await_args.args[0] == user.user_id


def test_unread_count_returns_current_users_count(monkeypatch) -> None:
    user = current_user()
    service = Mock()
    service.unread_count = AsyncMock(return_value=6)
    monkeypatch.setattr(
        notification_router_module,
        "_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.get("/api/v1/notifications/unread-count")

    assert response.status_code == 200
    assert response.json() == {"unread_count": 6}
    service.unread_count.assert_awaited_once_with(user.user_id)


def test_mark_read_is_recipient_scoped_by_authenticated_user(monkeypatch) -> None:
    user = current_user()
    notification = notification_record(user)
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    service = Mock()
    service.mark_read = AsyncMock(return_value=notification)
    monkeypatch.setattr(
        notification_router_module,
        "_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(f"/api/v1/notifications/{notification.id}/read")

    assert response.status_code == 200
    assert response.json()["is_read"] is True
    service.mark_read.assert_awaited_once_with(notification.id, user.user_id)


def test_wrong_recipient_notification_returns_not_found(monkeypatch) -> None:
    user = current_user()
    service = Mock()
    service.mark_read = AsyncMock(side_effect=NotFoundError("not found"))
    monkeypatch.setattr(
        notification_router_module,
        "_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(f"/api/v1/notifications/{uuid4()}/read")

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found"}


def test_read_all_returns_number_changed(monkeypatch) -> None:
    user = current_user()
    service = Mock()
    service.mark_all_read = AsyncMock(return_value=4)
    monkeypatch.setattr(
        notification_router_module,
        "_service",
        lambda session, authenticated_user: service,
    )
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post("/api/v1/notifications/read-all")

    assert response.status_code == 200
    assert response.json() == {"updated_count": 4}
    service.mark_all_read.assert_awaited_once_with(user.user_id)


def test_public_notification_creation_endpoint_does_not_exist(monkeypatch) -> None:
    user = current_user()
    application = build_application(monkeypatch, user)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/notifications",
            json={
                "recipient_user_id": str(uuid4()),
                "notification_type": "system_notice",
                "title": "Injected",
                "message": "Injected",
            },
        )

    assert response.status_code == 405
