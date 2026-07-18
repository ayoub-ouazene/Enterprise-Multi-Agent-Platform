from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.assistant.router as assistant_router_module
import app.main as main_module
from app.assistant.schemas import AssistantMessageResponse
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session
from app.llm.exceptions import RouterProviderError


def settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def application(monkeypatch, *, authenticated=True):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda value: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda value: Mock())
    app = main_module.create_app(settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    if authenticated:
        app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
            user_id=uuid4(),
            company_id=uuid4(),
            email="employee@example.com",
            actor_type=ActorType.EMPLOYEE,
        )
    return app


def test_assistant_endpoint_returns_typed_platform_response(monkeypatch) -> None:
    fake = Mock()
    fake.handle = AsyncMock(
        return_value=AssistantMessageResponse(
            message_category="platform_question",
            owner_department=None,
            request_id=None,
            request_status=None,
            needs_clarification=False,
            clarification_question=None,
            response="The platform supports five departments.",
            request_type=None,
            short_summary=None,
        )
    )
    monkeypatch.setattr(
        assistant_router_module,
        "_service",
        lambda session, user, settings: fake,
    )

    with TestClient(application(monkeypatch)) as client:
        response = client.post(
            "/api/v1/assistant/message",
            json={"message": "What departments are available?"},
        )

    assert response.status_code == 200
    assert response.json()["request_id"] is None
    assert response.json()["owner_department"] is None


def test_provider_error_is_sanitized(monkeypatch) -> None:
    fake = Mock()
    fake.handle = AsyncMock(
        side_effect=RouterProviderError("raw provider secret details")
    )
    monkeypatch.setattr(
        assistant_router_module,
        "_service",
        lambda session, user, settings: fake,
    )

    with TestClient(application(monkeypatch)) as client:
        response = client.post(
            "/api/v1/assistant/message",
            json={"message": "private content"},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "The Platform Assistant is temporarily unavailable"
    }
    assert "secret" not in response.text


def test_assistant_endpoint_requires_authentication(monkeypatch) -> None:
    with TestClient(application(monkeypatch, authenticated=False)) as client:
        response = client.post(
            "/api/v1/assistant/message",
            json={"message": "What departments are available?"},
        )

    assert response.status_code == 401
