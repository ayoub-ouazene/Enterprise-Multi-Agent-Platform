import asyncio
from datetime import UTC, datetime
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from starlette.datastructures import Headers, UploadFile

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.enums import ActorType
from app.rag.enums import (
    KnowledgeAccessScope,
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)
from app.rag.exceptions import KnowledgeConflictError, KnowledgeProviderError
from app.rag.ingestion import KnowledgeIngestionService
from app.rag.schemas import KnowledgeDocumentMetadata


def current(company_id=None):
    return AuthenticatedUser(
        user_id=uuid4(),
        company_id=company_id or uuid4(),
        email="owner@example.com",
        actor_type=ActorType.COMPANY,
    )


def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        alembic_database_url="postgresql+asyncpg://test:test@localhost/test",
        upload_directory=tmp_path,
        max_upload_size_mb=1,
        allowed_upload_extensions=["pdf", "docx", "txt"],
    )


def upload(content=b"Company leave policy.", filename="policy.txt", mime="text/plain"):
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": mime}),
    )


def metadata(title="Leave Policy"):
    return KnowledgeDocumentMetadata(
        title=title,
        document_type=KnowledgeDocumentType.POLICY,
        department_scope=[KnowledgeDepartmentScope.HR],
        access_scope=KnowledgeAccessScope.EMPLOYEES,
    )


def document(user, *, version=1, supersedes=None):
    return SimpleNamespace(
        id=uuid4(),
        company_id=user.company_id,
        uploaded_by_user_id=user.user_id,
        title="Leave Policy",
        original_filename="policy.txt",
        document_type=KnowledgeDocumentType.POLICY,
        department_scope=[KnowledgeDepartmentScope.HR],
        access_scope=KnowledgeAccessScope.EMPLOYEES,
        version=version,
        status=KnowledgeDocumentStatus.DRAFT,
        is_active=False,
        effective_date=None,
        supersedes_document_id=supersedes,
        mime_type="text/plain",
        file_size_bytes=21,
        checksum="a" * 64,
        chunk_count=0,
        ingestion_status=KnowledgeIngestionStatus.PENDING,
        ingestion_error_safe=None,
        ingested_at=None,
        deleted_at=None,
    )


def service_parts(tmp_path):
    user = current()
    record = document(user)
    session = SimpleNamespace(
        commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock()
    )

    async def completed(item, count):
        item.status = KnowledgeDocumentStatus.ACTIVE
        item.is_active = True
        item.ingestion_status = KnowledgeIngestionStatus.COMPLETED
        item.chunk_count = count

    async def processing(item):
        item.ingestion_status = KnowledgeIngestionStatus.PROCESSING

    async def failed(item, message):
        item.ingestion_status = KnowledgeIngestionStatus.FAILED
        item.ingestion_error_safe = message

    repository = SimpleNamespace(
        find_active_duplicate=AsyncMock(return_value=None),
        create_pending=AsyncMock(return_value=record),
        mark_processing=AsyncMock(side_effect=processing),
        mark_completed=AsyncMock(side_effect=completed),
        mark_failed=AsyncMock(side_effect=failed),
        mark_superseded=AsyncMock(),
        mark_deleted=AsyncMock(),
        get=AsyncMock(),
    )
    provider = SimpleNamespace(
        upsert=AsyncMock(),
        fetch=AsyncMock(side_effect=lambda _namespace, ids: set(ids)),
        delete=AsyncMock(),
    )
    company_repository = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(is_active=True))
    )
    service = KnowledgeIngestionService(
        session,
        user,
        settings(tmp_path),
        provider,
        repository=repository,
        department_repository=SimpleNamespace(),
        company_repository=company_repository,
    )
    return service, record, repository, provider, session


def test_successful_ingestion_uses_company_namespace_and_completes(tmp_path) -> None:
    service, record, repository, provider, _ = service_parts(tmp_path)
    result = asyncio.run(service.create(upload(), metadata()))
    assert result is record
    assert record.ingestion_status == KnowledgeIngestionStatus.COMPLETED
    assert record.chunk_count > 0
    assert provider.upsert.await_args.args[0] == f"company_{service.current_user.company_id}"
    records = provider.upsert.await_args.args[1]
    assert records[0]["_id"] == f"{record.id}:1:0000"
    assert records[0]["company_id"] == str(service.current_user.company_id)
    assert list(tmp_path.iterdir()) == []


def test_duplicate_checksum_is_rejected_without_leaving_upload(tmp_path) -> None:
    service, _, repository, _, _ = service_parts(tmp_path)
    repository.find_active_duplicate.return_value = SimpleNamespace(id=uuid4())
    with pytest.raises(KnowledgeConflictError):
        asyncio.run(service.create(upload(), metadata()))
    assert list(tmp_path.iterdir()) == []


def test_provider_failure_marks_safe_failed_state_and_compensates(tmp_path) -> None:
    service, record, repository, provider, _ = service_parts(tmp_path)
    provider.upsert.side_effect = KnowledgeProviderError("Knowledge service unavailable")
    service._notify_failure = AsyncMock()
    with pytest.raises(KnowledgeProviderError):
        asyncio.run(service.create(upload(), metadata()))
    assert record.ingestion_status == KnowledgeIngestionStatus.FAILED
    assert "unavailable" in record.ingestion_error_safe
    service._notify_failure.assert_awaited_once_with(record)
    assert list(tmp_path.iterdir()) == []


def test_replacement_activates_new_version_before_old_cleanup(tmp_path) -> None:
    service, replacement, repository, provider, _ = service_parts(tmp_path)
    previous = document(service.current_user)
    previous.status = KnowledgeDocumentStatus.ACTIVE
    previous.is_active = True
    previous.ingestion_status = KnowledgeIngestionStatus.COMPLETED
    previous.chunk_count = 1
    replacement.version = 2
    replacement.supersedes_document_id = previous.id
    repository.get.return_value = previous

    async def supersede(item):
        item.status = KnowledgeDocumentStatus.SUPERSEDED
        item.is_active = False

    repository.mark_superseded.side_effect = supersede
    result = asyncio.run(
        service.replace(previous.id, upload(b"Updated leave policy."), metadata())
    )
    assert result.version == 2
    assert previous.status == KnowledgeDocumentStatus.SUPERSEDED
    provider.delete.assert_awaited_with(
        f"company_{service.current_user.company_id}",
        [f"{previous.id}:1:0000"],
    )


def test_deletion_targets_only_trusted_company_namespace(tmp_path) -> None:
    service, record, repository, provider, _ = service_parts(tmp_path)
    record.status = KnowledgeDocumentStatus.ACTIVE
    record.chunk_count = 2
    repository.get.return_value = record

    async def deleted(item):
        item.status = KnowledgeDocumentStatus.DELETED

    repository.mark_deleted.side_effect = deleted
    asyncio.run(service.delete(record.id))
    provider.delete.assert_awaited_once_with(
        f"company_{service.current_user.company_id}",
        [f"{record.id}:1:0000", f"{record.id}:1:0001"],
    )
    assert record.status == KnowledgeDocumentStatus.DELETED


def test_oversized_and_path_traversal_uploads_are_handled(tmp_path) -> None:
    service, _, _, _, _ = service_parts(tmp_path)
    service.settings.max_upload_size_mb = 1
    with pytest.raises(Exception, match="size limit"):
        asyncio.run(
            service.create(
                upload(b"x" * (1024 * 1024 + 1), "../../secret.txt"), metadata()
            )
        )
    assert list(tmp_path.iterdir()) == []
