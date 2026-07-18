from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.auth.router as auth_router_module
import app.main as main_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.auth.service import AuthenticationError, TokenPair
from app.auth.tokens import (
    TokenValidationError,
    create_access_token,
    decode_refresh_token,
)
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def build_context() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="owner@example.com",
        actor_type=ActorType.COMPANY,
    )


def build_application(monkeypatch):
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
    return application


def test_successful_login_returns_access_and_refresh_tokens(monkeypatch) -> None:
    pair = TokenPair("access-value", "refresh-value", 1800, 604800)

    class FakeService:
        def __init__(self, session, settings):
            pass

        async def login(self, company_slug, email, password):
            assert (company_slug, email, password) == (
                "acme",
                "owner@example.com",
                "correct horse battery staple",
            )
            return pair

    monkeypatch.setattr(auth_router_module, "AuthenticationService", FakeService)
    application = build_application(monkeypatch)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "company_slug": "acme",
                "email": "owner@example.com",
                "password": "correct horse battery staple",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-value",
        "refresh_token": "refresh-value",
        "token_type": "bearer",
        "access_token_expires_in": 1800,
        "refresh_token_expires_in": 604800,
    }
    assert "password_hash" not in response.text


def test_login_failure_uses_generic_authentication_error(monkeypatch) -> None:
    class RejectingService:
        def __init__(self, session, settings):
            pass

        async def login(self, company_slug, email, password):
            raise AuthenticationError("internal detail must not escape")

    monkeypatch.setattr(auth_router_module, "AuthenticationService", RejectingService)
    application = build_application(monkeypatch)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "company_slug": "unknown",
                "email": "unknown@example.com",
                "password": "incorrect password",
            },
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication credentials"}


def test_access_token_is_rejected_by_refresh_endpoint(monkeypatch) -> None:
    settings = build_settings()
    access_token = create_access_token(build_context(), settings).value

    class TokenCheckingService:
        def __init__(self, session, current_settings):
            self.settings = current_settings

        async def refresh(self, token):
            try:
                decode_refresh_token(token, self.settings)
            except TokenValidationError:
                raise AuthenticationError("wrong token purpose") from None
            raise AssertionError("An access token must never pass refresh validation")

    monkeypatch.setattr(
        auth_router_module, "AuthenticationService", TokenCheckingService
    )
    application = build_application(monkeypatch)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication credentials"}


def test_auth_me_returns_safe_authenticated_user(monkeypatch) -> None:
    context = build_context()
    application = build_application(monkeypatch)
    application.dependency_overrides[require_authenticated_user] = lambda: context

    with TestClient(application) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(context.user_id),
        "company_id": str(context.company_id),
        "email": context.email,
        "actor_type": "company",
        "employee_id": None,
        "department_id": None,
        "is_manager": False,
        "permissions": [],
    }
    assert "password_hash" not in response.text


def test_auth_me_without_token_is_rejected(monkeypatch) -> None:
    application = build_application(monkeypatch)

    with TestClient(application) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication credentials"}
