from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import app.main as main_module
import app.rag.router as router_module
from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.config import Settings
from app.core.enums import ActorType
from app.database.session import get_db_session
from app.rag.dependencies import get_pinecone_provider
from app.rag.enums import (
    KnowledgeAccessScope,
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)


def settings():
    return Settings(
        _env_file=None,
        app_env="test",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret_key="test-only-secret-key-that-is-at-least-32-bytes",
    )


def user(actor):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=uuid4(),
        email="user@example.com",
        actor_type=actor,
    )


def application(monkeypatch, current):
    engine = Mock()
    engine.dispose = AsyncMock()
    monkeypatch.setattr(main_module, "create_database_engine", lambda _: engine)
    monkeypatch.setattr(main_module, "create_session_factory", lambda _: Mock())
    app = main_module.create_app(settings())

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[require_authenticated_user] = lambda: current
    app.dependency_overrides[get_pinecone_provider] = lambda: SimpleNamespace(
        close=AsyncMock()
    )
    return app


def document():
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid4(),
        title="HR Policy",
        original_filename="policy.txt",
        document_type=KnowledgeDocumentType.POLICY,
        department_scope=[KnowledgeDepartmentScope.HR],
        access_scope=KnowledgeAccessScope.EMPLOYEES,
        version=1,
        status=KnowledgeDocumentStatus.ACTIVE,
        is_active=True,
        effective_date=None,
        supersedes_document_id=None,
        mime_type="text/plain",
        file_size_bytes=10,
        chunk_count=1,
        ingestion_status=KnowledgeIngestionStatus.COMPLETED,
        ingestion_error_safe=None,
        custom_metadata={},
        created_at=now,
        updated_at=now,
        ingested_at=now,
        deleted_at=None,
        password_hash="must-never-appear",
    )


def test_company_can_upload_document_without_sensitive_fields(monkeypatch) -> None:
    service = SimpleNamespace(create=AsyncMock(return_value=document()))
    monkeypatch.setattr(router_module, "_ingestion_service", lambda *_: service)
    with TestClient(application(monkeypatch, user(ActorType.COMPANY))) as client:
        response = client.post(
            "/api/v1/documents",
            files={"file": ("policy.txt", b"HR policy", "text/plain")},
            data={
                "title": "HR Policy",
                "document_type": "policy",
                "department_scope": "hr",
                "access_scope": "employees",
                "custom_metadata": "{}",
            },
        )
    assert response.status_code == 201
    assert "password_hash" not in response.text
    assert "stored_filename" not in response.text


def test_employee_document_management_is_rejected(monkeypatch) -> None:
    with TestClient(application(monkeypatch, user(ActorType.EMPLOYEE))) as client:
        response = client.get("/api/v1/documents")
    assert response.status_code == 403


def test_all_step_12_routes_are_registered(monkeypatch) -> None:
    app = application(monkeypatch, user(ActorType.COMPANY))
    routes = {(method, route.path) for route in app.routes for method in getattr(route, "methods", set())}
    expected = {
        ("POST", "/api/v1/documents"),
        ("GET", "/api/v1/documents"),
        ("GET", "/api/v1/documents/{document_id}"),
        ("POST", "/api/v1/documents/{document_id}/replace"),
        ("POST", "/api/v1/documents/{document_id}/retry-ingestion"),
        ("DELETE", "/api/v1/documents/{document_id}"),
        ("POST", "/api/v1/documents/search"),
    }
    assert expected.issubset(routes)
