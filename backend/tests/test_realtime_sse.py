from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.realtime.dependencies import get_current_user_for_sse
from app.workflow.enums import WorkflowEventType, WorkflowEventVisibility


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
        sse_heartbeat_seconds=1,
    )


def current_user(
    actor_type: ActorType = ActorType.EMPLOYEE,
) -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="employee@example.com",
        actor_type=actor_type,
        employee_id=uuid4(),
    )


def _make_async_cm_mock(session_instance):
    """Return a callable that works as an async context manager."""
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session_instance)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


def _mock_session_factory_for_router(session_instance):
    def _factory(request):
        return _make_async_cm_mock(session_instance)
    return _factory


def _patch_sleep_to_exit_after_iterations(max_iterations: int = 1):
    call_count = 0
    async def limited_sleep(_delay):
        nonlocal call_count
        call_count += 1
        if call_count > max_iterations:
            raise GeneratorExit()
    return patch("app.realtime.service._sleep", limited_sleep)


def _apply_session_factory_patch(session_instance):
    return patch(
        "app.realtime.router._session_factory",
        new=_mock_session_factory_for_router(session_instance),
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

    if user is not None:
        async def user_override():
            return user
        application.dependency_overrides[get_current_user_for_sse] = user_override
    return application


class MockEvent:
    def __init__(self, seq: int, visibility: WorkflowEventVisibility, *, actor: str = "user"):
        self.id = uuid4()
        self.request_id = uuid4()
        self.event_type = WorkflowEventType.STAGE_STARTED
        self.stage = "test"
        self.title = "Test"
        self.message = "Test message"
        self.actor_type = actor
        self.actor_user_id = None
        self.department_id = None
        self.visibility = visibility
        self.event_data = {}
        self.sequence_number = seq
        self.created_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def test_workflow_stream_requires_authentication(monkeypatch) -> None:
    application = build_application(monkeypatch, user=None)
    application.dependency_overrides.pop(get_current_user_for_sse, None)

    with TestClient(application) as client:
        response = client.get(
            f"/api/v1/requests/{uuid4()}/events/stream",
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 401


def test_notification_stream_requires_authentication(monkeypatch) -> None:
    application = build_application(monkeypatch, user=None)
    application.dependency_overrides.pop(get_current_user_for_sse, None)

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/notifications/stream",
            headers={"Accept": "text/event-stream"},
        )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Connection limit
# ---------------------------------------------------------------------------


def test_connection_limit_rejects_new_streams(monkeypatch) -> None:
    user = current_user()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.router._authorize_request_access",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.realtime.service._acquire_connection",
                new_callable=AsyncMock,
                return_value=False,
            ):
                with TestClient(application) as client:
                    response = client.get(
                        f"/api/v1/requests/{uuid4()}/events/stream",
                        headers={"Accept": "text/event-stream"},
                    )

    assert response.status_code == 200
    body = response.text
    assert "error" in body
    assert "maximum capacity" in body


# ---------------------------------------------------------------------------
# Workflow event streams
# ---------------------------------------------------------------------------


def test_workflow_stream_replays_events_after_cursor(monkeypatch) -> None:
    user = current_user()
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=1, visibility=WorkflowEventVisibility.REQUESTER),
        MockEvent(seq=2, visibility=WorkflowEventVisibility.REQUESTER),
        MockEvent(seq=3, visibility=WorkflowEventVisibility.INTERNAL),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream?last_event_id=1",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    body = response.text
    assert '"sequence_number": 2' in body
    assert '"sequence_number": 3' not in body


def test_workflow_stream_filters_internal_events_for_requester(monkeypatch) -> None:
    user = current_user(actor_type=ActorType.EMPLOYEE)
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=1, visibility=WorkflowEventVisibility.REQUESTER),
        MockEvent(seq=2, visibility=WorkflowEventVisibility.INTERNAL),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    body = response.text
    assert '"sequence_number": 1' in body
    assert '"sequence_number": 2' not in body


def test_workflow_stream_shows_manager_events_for_manager(monkeypatch) -> None:
    user = AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="manager@example.com",
        actor_type=ActorType.DEPARTMENT_MANAGER,
        employee_id=uuid4(),
        department_id=uuid4(),
        is_manager=True,
    )
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=1, visibility=WorkflowEventVisibility.REQUESTER),
        MockEvent(seq=2, visibility=WorkflowEventVisibility.MANAGER),
        MockEvent(seq=3, visibility=WorkflowEventVisibility.INTERNAL),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    body = response.text
    assert '"sequence_number": 1' in body
    assert '"sequence_number": 2' in body
    assert '"sequence_number": 3' not in body


def test_workflow_stream_shows_internal_for_company_account(monkeypatch) -> None:
    user = current_user(actor_type=ActorType.COMPANY)
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=1, visibility=WorkflowEventVisibility.INTERNAL),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    body = response.text
    assert '"sequence_number": 1' in body


# ---------------------------------------------------------------------------
# Notification streams
# ---------------------------------------------------------------------------


def test_notification_stream_delivers_user_notifications(monkeypatch) -> None:
    user = current_user()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    from app.notifications.enums import NotificationType, NotificationSeverity

    class FakeNotification:
        pass

    notification = FakeNotification()
    notification.id = uuid4()
    notification.recipient_user_id = user.user_id
    notification.request_id = None
    notification.notification_type = NotificationType.REQUEST_CREATED
    notification.title = "Test"
    notification.message = "Test message"
    notification.severity = NotificationSeverity.INFO
    notification.action_required = False
    notification.action_type = None
    notification.action_url = None
    notification.is_read = False
    notification.read_at = None
    notification.created_at = datetime.now(UTC)
    notification.expires_at = None

    async def mock_list_for_recipient(self, recipient_user_id, *_, **kwargs):
        if notification.recipient_user_id == recipient_user_id:
            return [notification]
        return []

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.NotificationRepository.list_for_recipient",
            new=mock_list_for_recipient,
        ):
            with patch(
                "app.realtime.service._release_connection",
                new_callable=AsyncMock,
            ):
                with _patch_sleep_to_exit_after_iterations(5):
                    with TestClient(application) as client:
                        response = client.get(
                            "/api/v1/notifications/stream",
                            headers={"Accept": "text/event-stream"},
                        )

    assert response.status_code == 200
    body = response.text
    assert "notification" in body
    assert "Test" in body


def test_notification_stream_only_delivers_own_notifications(monkeypatch) -> None:
    user = current_user()
    other_user_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    from app.notifications.enums import NotificationType, NotificationSeverity

    class FakeNotification:
        pass

    notification = FakeNotification()
    notification.id = uuid4()
    notification.recipient_user_id = other_user_id
    notification.request_id = None
    notification.notification_type = NotificationType.REQUEST_CREATED
    notification.title = "Other"
    notification.message = "Other message"
    notification.severity = NotificationSeverity.INFO
    notification.action_required = False
    notification.action_type = None
    notification.action_url = None
    notification.is_read = False
    notification.read_at = None
    notification.created_at = datetime.now(UTC)
    notification.expires_at = None

    async def mock_list_for_recipient(self, recipient_user_id, *_, **kwargs):
        if notification.recipient_user_id == recipient_user_id:
            return [notification]
        return []

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.NotificationRepository.list_for_recipient",
            new=mock_list_for_recipient,
        ):
            with patch(
                "app.realtime.service._release_connection",
                new_callable=AsyncMock,
            ):
                with _patch_sleep_to_exit_after_iterations(5):
                    with TestClient(application) as client:
                        response = client.get(
                            "/api/v1/notifications/stream",
                            headers={"Accept": "text/event-stream"},
                        )

    assert response.status_code == 200
    body = response.text
    assert "Other" not in body


# ---------------------------------------------------------------------------
# Authorization / cross-company
# ---------------------------------------------------------------------------


def test_workflow_stream_returns_404_for_inaccessible_request(monkeypatch) -> None:
    user = current_user()
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.router._authorize_request_access",
            new_callable=AsyncMock,
            side_effect=NotFoundError("Business request not found"),
        ):
            with patch(
                "app.realtime.service._release_connection",
                new_callable=AsyncMock,
            ):
                with _patch_sleep_to_exit_after_iterations(5):
                    with TestClient(application) as client:
                        response = client.get(
                            f"/api/v1/requests/{request_id}/events/stream",
                            headers={"Accept": "text/event-stream"},
                        )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Cursor / replay
# ---------------------------------------------------------------------------


def test_workflow_stream_last_event_id_is_sequence_number(monkeypatch) -> None:
    user = current_user()
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=5, visibility=WorkflowEventVisibility.REQUESTER),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream?last_event_id=4",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    assert "id: 5" in response.text


def test_notification_stream_cursor_format(monkeypatch) -> None:
    user = current_user()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    from app.notifications.enums import NotificationType, NotificationSeverity

    now = datetime.now(UTC)
    nid = uuid4()

    class FakeNotification:
        pass

    notification = FakeNotification()
    notification.id = nid
    notification.recipient_user_id = user.user_id
    notification.request_id = None
    notification.notification_type = NotificationType.REQUEST_CREATED
    notification.title = "Test"
    notification.message = "Test message"
    notification.severity = NotificationSeverity.INFO
    notification.action_required = False
    notification.action_type = None
    notification.action_url = None
    notification.is_read = False
    notification.read_at = None
    notification.created_at = now
    notification.expires_at = None

    async def mock_list_for_recipient(self, recipient_user_id, *_, **kwargs):
        if notification.recipient_user_id == recipient_user_id:
            return [notification]
        return []

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.NotificationRepository.list_for_recipient",
            new=mock_list_for_recipient,
        ):
            with patch(
                "app.realtime.service._release_connection",
                new_callable=AsyncMock,
            ):
                with _patch_sleep_to_exit_after_iterations(5):
                    with TestClient(application) as client:
                        response = client.get(
                            "/api/v1/notifications/stream",
                            headers={"Accept": "text/event-stream"},
                        )

    assert response.status_code == 200
    body = response.text
    expected_id = f"id: {now.isoformat()}_{nid}"
    assert expected_id in body


# ---------------------------------------------------------------------------
# Data exposure
# ---------------------------------------------------------------------------


def test_workflow_stream_excludes_private_fields(monkeypatch) -> None:
    user = current_user()
    request_id = uuid4()
    application = build_application(monkeypatch, user)
    session = AsyncMock()

    events = [
        MockEvent(seq=1, visibility=WorkflowEventVisibility.REQUESTER),
    ]

    async def mock_list_for_request(*_, **kwargs):
        vis = kwargs.get("visibilities", frozenset())
        return [e for e in events if e.visibility in vis]

    with _apply_session_factory_patch(session):
        with patch(
            "app.realtime.service.WorkflowEventRepository.list_for_request",
            new=mock_list_for_request,
        ):
            with patch(
                "app.realtime.router._authorize_request_access",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.realtime.service._release_connection",
                    new_callable=AsyncMock,
                ):
                    with _patch_sleep_to_exit_after_iterations(5):
                        with TestClient(application) as client:
                            response = client.get(
                                f"/api/v1/requests/{request_id}/events/stream",
                                headers={"Accept": "text/event-stream"},
                            )

    assert response.status_code == 200
    body = response.text
    assert "actor_user_id" not in body
    assert "company_id" not in body
    assert "visibility" not in body
