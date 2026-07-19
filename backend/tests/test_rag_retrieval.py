import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType, DepartmentType
from app.rag.enums import (
    KnowledgeAccessScope,
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)
from app.rag.exceptions import KnowledgePermissionError
from app.rag.retrieval import KnowledgeRetrievalService
from app.rag.schemas import KnowledgeSearchRequest


def settings() -> Settings:
    return Settings(
        _env_file=None,
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        rag_top_k=8,
    )


def current(actor: ActorType, *, company_id=None, department_id=None):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="user@example.com",
        actor_type=actor,
        employee_id=uuid4() if department_id else None,
        department_id=department_id,
        is_manager=actor == ActorType.DEPARTMENT_MANAGER,
    )


def document(company_id, document_id):
    return SimpleNamespace(
        id=document_id,
        company_id=company_id,
        version=1,
        is_active=True,
        status=KnowledgeDocumentStatus.ACTIVE,
        ingestion_status=KnowledgeIngestionStatus.COMPLETED,
    )


def hit(company_id, document_id, **changes):
    value = {
        "_id": f"{document_id}:1:0000",
        "_score": 0.91,
        "chunk_text": "Approved policy text",
        "company_id": str(company_id),
        "document_id": str(document_id),
        "document_title": "Policy",
        "document_type": "policy",
        "departments": ["hr"],
        "access_scope": "employees",
        "version": 1,
        "chunk_index": 0,
        "source_filename": "policy.txt",
    }
    value.update(changes)
    return value


def test_company_search_uses_only_company_namespace_and_filters() -> None:
    company_id, document_id = uuid4(), uuid4()
    user = current(ActorType.COMPANY, company_id=company_id)
    provider = SimpleNamespace(search=AsyncMock(return_value=[hit(company_id, document_id)]))
    repository = SimpleNamespace(
        active_by_ids=AsyncMock(return_value={document_id: document(company_id, document_id)})
    )
    service = KnowledgeRetrievalService(
        AsyncMock(), user, settings(), provider, repository=repository
    )
    result = asyncio.run(service.search(KnowledgeSearchRequest(query_text="leave", top_k=20)))
    assert len(result) == 1
    call = provider.search.await_args
    assert call.args[0] == f"company_{company_id}"
    assert call.kwargs["top_k"] == 8
    assert {"company_id": {"$eq": str(company_id)}} in call.kwargs["metadata_filter"]["$and"]


def test_inactive_postgres_document_is_excluded() -> None:
    company_id, document_id = uuid4(), uuid4()
    provider = SimpleNamespace(search=AsyncMock(return_value=[hit(company_id, document_id)]))
    repository = SimpleNamespace(active_by_ids=AsyncMock(return_value={}))
    service = KnowledgeRetrievalService(
        AsyncMock(), current(ActorType.COMPANY, company_id=company_id), settings(), provider,
        repository=repository,
    )
    assert asyncio.run(service.search(KnowledgeSearchRequest(query_text="policy"))) == []


def test_malformed_and_cross_tenant_hits_are_ignored() -> None:
    company_id = uuid4()
    provider = SimpleNamespace(
        search=AsyncMock(
            return_value=[{"bad": "shape"}, hit(uuid4(), uuid4())]
        )
    )
    repository = SimpleNamespace(active_by_ids=AsyncMock(return_value={}))
    service = KnowledgeRetrievalService(
        AsyncMock(), current(ActorType.COMPANY, company_id=company_id), settings(), provider,
        repository=repository,
    )
    assert asyncio.run(service.search(KnowledgeSearchRequest(query_text="policy"))) == []


def test_manager_is_restricted_to_own_and_shared_department() -> None:
    department_id = uuid4()
    user = current(ActorType.DEPARTMENT_MANAGER, department_id=department_id)
    department_repository = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                id=department_id,
                is_active=True,
                department_type=DepartmentType.HR,
            )
        )
    )
    service = KnowledgeRetrievalService(
        AsyncMock(), user, settings(), SimpleNamespace(),
        repository=SimpleNamespace(),
        department_repository=department_repository,
    )
    with pytest.raises(KnowledgePermissionError):
        asyncio.run(
            service.trusted_query(
                KnowledgeSearchRequest(
                    query_text="budget", department=KnowledgeDepartmentScope.FINANCE
                )
            )
        )
    trusted = asyncio.run(service.trusted_query(KnowledgeSearchRequest(query_text="leave")))
    assert trusted.departments == [
        KnowledgeDepartmentScope.HR,
        KnowledgeDepartmentScope.SHARED,
    ]
    assert KnowledgeAccessScope.COMPANY_ACCOUNT not in trusted.allowed_access_scopes
