import asyncio
import hashlib
import logging
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, time
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.companies.repository import CompanyRepository
from app.core.config import BACKEND_DIRECTORY, Settings
from app.core.enums import ActorType
from app.departments.repository import DepartmentRepository
from app.notifications.enums import NotificationSeverity, NotificationType
from app.notifications.schemas import NotificationCreate
from app.notifications.service import NotificationService
from app.rag.chunking import chunk_text
from app.rag.enums import (
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeIngestionStatus,
)
from app.rag.exceptions import (
    KnowledgeConflictError,
    KnowledgeError,
    KnowledgeExtractionError,
    KnowledgeNotFoundError,
    KnowledgePermissionError,
    KnowledgeProviderError,
    KnowledgeValidationError,
)
from app.rag.extractors import (
    SUPPORTED_EXTENSIONS,
    clean_text,
    extract_document,
    validate_file_signature,
)
from app.rag.models import KnowledgeDocument
from app.rag.namespace import build_chunk_id, build_company_namespace
from app.rag.permissions import (
    authorize_document_management,
    authorize_metadata,
    trusted_manager_department,
)
from app.rag.pinecone import PineconeProvider
from app.rag.repository import KnowledgeDocumentRepository
from app.rag.schemas import KnowledgeDocumentListFilters, KnowledgeDocumentMetadata


logger = logging.getLogger(__name__)
STREAM_BLOCK_SIZE = 64 * 1024


@dataclass(frozen=True, slots=True)
class SavedUpload:
    path: Path
    original_filename: str
    extension: str
    mime_type: str
    size: int
    checksum: str


def _safe_filename(value: str | None) -> str:
    candidate = Path((value or "document").replace("\\", "/")).name
    candidate = unicodedata.normalize("NFKC", candidate)
    candidate = "".join(char for char in candidate if char.isprintable()).strip(" .")
    if not candidate:
        candidate = "document"
    return candidate[:255]


class KnowledgeIngestionService:
    def __init__(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        settings: Settings,
        provider: PineconeProvider,
        *,
        repository: KnowledgeDocumentRepository | None = None,
        department_repository: DepartmentRepository | None = None,
        company_repository: CompanyRepository | None = None,
    ) -> None:
        self.session = session
        self.current_user = current_user
        self.settings = settings
        self.provider = provider
        self.repository = repository or KnowledgeDocumentRepository(
            session, current_user.company_id
        )
        self.department_repository = department_repository or DepartmentRepository(
            session, current_user.company_id
        )
        self.company_repository = company_repository or CompanyRepository(session)

    async def _authorize_company(self) -> None:
        if self.current_user.actor_type not in {
            ActorType.COMPANY,
            ActorType.DEPARTMENT_MANAGER,
        }:
            raise KnowledgePermissionError("Knowledge management access is required")
        company = await self.company_repository.get_by_id(self.current_user.company_id)
        if company is None or not company.is_active:
            raise KnowledgePermissionError("An active company is required")

    def _upload_directory(self) -> Path:
        configured = self.settings.upload_directory
        directory = configured if configured.is_absolute() else BACKEND_DIRECTORY / configured
        directory = directory.resolve()
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    async def _save_upload(self, upload: UploadFile) -> SavedUpload:
        filename = _safe_filename(upload.filename)
        extension = Path(filename).suffix.lower().lstrip(".")
        allowed = {item.lower().lstrip(".") for item in self.settings.allowed_upload_extensions}
        if extension not in SUPPORTED_EXTENSIONS or extension not in allowed:
            raise KnowledgeValidationError("Unsupported knowledge-document file type")
        mime_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
        path = self._upload_directory() / f"{uuid4().hex}.upload"
        maximum = self.settings.max_upload_size_mb * 1024 * 1024
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("xb") as destination:
                while block := await upload.read(STREAM_BLOCK_SIZE):
                    size += len(block)
                    if size > maximum:
                        raise KnowledgeValidationError("Uploaded document exceeds the size limit")
                    digest.update(block)
                    destination.write(block)
            if size == 0:
                raise KnowledgeValidationError("Uploaded document is empty")
            await asyncio.to_thread(validate_file_signature, path, extension, mime_type)
            return SavedUpload(path, filename, extension, mime_type, size, digest.hexdigest())
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

    def _record_ids(self, document: KnowledgeDocument, count: int | None = None) -> list[str]:
        return [
            build_chunk_id(document.id, document.version, index)
            for index in range(document.chunk_count if count is None else count)
        ]

    async def _records(self, document: KnowledgeDocument, saved: SavedUpload):
        extracted = await asyncio.to_thread(extract_document, saved.path, saved.extension)
        cleaned = clean_text(extracted.text)
        chunks = chunk_text(
            cleaned,
            chunk_size=self.settings.rag_chunk_size,
            overlap=self.settings.rag_chunk_overlap,
            embedding_model=self.settings.pinecone_embedding_model,
        )
        effective_epoch = None
        if document.effective_date is not None:
            effective_epoch = int(
                datetime.combine(document.effective_date, time.min, tzinfo=UTC).timestamp()
            )
        records = []
        for chunk in chunks:
            record = {
                "_id": build_chunk_id(document.id, document.version, chunk.index),
                "chunk_text": chunk.text,
                "company_id": str(document.company_id),
                "document_id": str(document.id),
                "document_title": document.title,
                "document_type": document.document_type.value,
                "departments": [scope.value for scope in document.department_scope],
                "access_scope": document.access_scope.value,
                "version": document.version,
                "is_active": True,
                "chunk_index": chunk.index,
                "source_filename": document.original_filename,
            }
            if document.effective_date is not None:
                record["effective_date"] = document.effective_date.isoformat()
                record["effective_date_epoch"] = effective_epoch
            records.append(record)
        return records

    async def _verify_records(self, namespace: str, ids: list[str]) -> None:
        expected = set(ids)
        for delay in (0.0, 0.25, 0.5, 1.0):
            if delay:
                await asyncio.sleep(delay)
            found = await self.provider.fetch(namespace, ids)
            if expected.issubset(found):
                return
        raise KnowledgeProviderError("Knowledge records were not confirmed after ingestion")

    async def _notify_failure(self, document: KnowledgeDocument) -> None:
        try:
            await NotificationService(
                self.session, self.current_user.company_id
            ).create(
                NotificationCreate(
                    recipient_user_id=document.uploaded_by_user_id,
                    notification_type=NotificationType.SYSTEM_NOTICE,
                    title="Document ingestion failed",
                    message="The document could not be added to company knowledge.",
                    severity=NotificationSeverity.ERROR,
                    metadata={"document_id": str(document.id)},
                )
            )
        except Exception:
            await self.session.rollback()
            logger.warning(
                "Knowledge failure notification failed company_id=%s document_id=%s",
                self.current_user.company_id,
                document.id,
            )

    async def _ingest_saved(
        self,
        document: KnowledgeDocument,
        saved: SavedUpload,
        *,
        previous: KnowledgeDocument | None = None,
    ) -> KnowledgeDocument:
        namespace = build_company_namespace(
            self.current_user.company_id, self.settings.pinecone_namespace_prefix
        )
        records: list[dict] = []
        try:
            await self.repository.mark_processing(document)
            await self.session.commit()
            records = await self._records(document, saved)
            await self.provider.upsert(namespace, records)
            ids = [record["_id"] for record in records]
            await self._verify_records(namespace, ids)
            await self.repository.mark_completed(document, len(records))
            if previous is not None:
                await self.repository.mark_superseded(previous)
            await self.session.commit()
            await self.session.refresh(document)
            if previous is not None:
                try:
                    await self.provider.delete(namespace, self._record_ids(previous))
                except KnowledgeProviderError:
                    logger.warning(
                        "Superseded knowledge cleanup failed company_id=%s document_id=%s",
                        self.current_user.company_id,
                        previous.id,
                    )
            return document
        except Exception as exc:
            await self.session.rollback()
            if records:
                try:
                    await self.provider.delete(
                        namespace, [str(record["_id"]) for record in records]
                    )
                except Exception:
                    logger.warning(
                        "Knowledge compensation failed company_id=%s document_id=%s",
                        self.current_user.company_id,
                        document.id,
                    )
            safe_error = (
                str(exc)
                if isinstance(exc, KnowledgeError)
                else "Document ingestion failed unexpectedly"
            )
            await self.repository.mark_failed(document, safe_error)
            await self.session.commit()
            await self._notify_failure(document)
            logger.warning(
                "Knowledge ingestion failed company_id=%s document_id=%s file_type=%s file_size=%s",
                self.current_user.company_id,
                document.id,
                saved.extension,
                saved.size,
            )
            if isinstance(exc, KnowledgeError):
                raise exc from None
            raise KnowledgeExtractionError(safe_error) from None
        finally:
            saved.path.unlink(missing_ok=True)

    async def create(
        self, upload: UploadFile, metadata: KnowledgeDocumentMetadata
    ) -> KnowledgeDocument:
        await self._authorize_company()
        await authorize_metadata(
            self.current_user, metadata, self.department_repository
        )
        await self.session.rollback()
        saved = await self._save_upload(upload)
        try:
            duplicate = await self.repository.find_active_duplicate(saved.checksum)
            if duplicate is not None:
                raise KnowledgeConflictError("This document is already active")
            document = await self.repository.create_pending(
                uploaded_by_user_id=self.current_user.user_id,
                metadata=metadata,
                original_filename=saved.original_filename,
                mime_type=saved.mime_type,
                file_size_bytes=saved.size,
                checksum=saved.checksum,
            )
            await self.session.commit()
            return await self._ingest_saved(document, saved)
        except Exception:
            if saved.path.exists():
                saved.path.unlink(missing_ok=True)
            await self.session.rollback()
            raise

    async def replace(
        self,
        document_id: UUID,
        upload: UploadFile,
        metadata: KnowledgeDocumentMetadata,
    ) -> KnowledgeDocument:
        await self._authorize_company()
        previous = await self.repository.get(document_id)
        if previous is None or previous.status == KnowledgeDocumentStatus.DELETED:
            raise KnowledgeNotFoundError("Knowledge document not found")
        await authorize_document_management(
            self.current_user, previous, self.department_repository
        )
        await authorize_metadata(self.current_user, metadata, self.department_repository)
        expected_version = previous.version
        await self.session.rollback()
        saved = await self._save_upload(upload)
        try:
            previous = await self.repository.get(document_id, for_update=True)
            if (
                previous is None
                or previous.status != KnowledgeDocumentStatus.ACTIVE
                or previous.version != expected_version
            ):
                raise KnowledgeConflictError("The document changed before replacement")
            duplicate = await self.repository.find_active_duplicate(saved.checksum)
            if duplicate is not None:
                raise KnowledgeConflictError("This document is already active")
            replacement = await self.repository.create_pending(
                uploaded_by_user_id=self.current_user.user_id,
                metadata=metadata,
                original_filename=saved.original_filename,
                mime_type=saved.mime_type,
                file_size_bytes=saved.size,
                checksum=saved.checksum,
                version=previous.version + 1,
                supersedes_document_id=previous.id,
            )
            await self.session.commit()
            return await self._ingest_saved(replacement, saved, previous=previous)
        except IntegrityError:
            saved.path.unlink(missing_ok=True)
            await self.session.rollback()
            raise KnowledgeConflictError("A replacement already exists") from None
        except Exception:
            saved.path.unlink(missing_ok=True)
            await self.session.rollback()
            raise

    async def retry(self, document_id: UUID, upload: UploadFile) -> KnowledgeDocument:
        await self._authorize_company()
        document = await self.repository.get(document_id)
        if document is None:
            raise KnowledgeNotFoundError("Knowledge document not found")
        await authorize_document_management(
            self.current_user, document, self.department_repository
        )
        if document.ingestion_status != KnowledgeIngestionStatus.FAILED:
            raise KnowledgeConflictError("Only failed ingestion can be retried")
        expected_checksum = document.checksum
        await self.session.rollback()
        saved = await self._save_upload(upload)
        if saved.checksum != expected_checksum:
            saved.path.unlink(missing_ok=True)
            raise KnowledgeConflictError("Retry file must match the original document")
        document = await self.repository.get(document_id, for_update=True)
        if (
            document is None
            or document.ingestion_status != KnowledgeIngestionStatus.FAILED
            or document.checksum != expected_checksum
        ):
            saved.path.unlink(missing_ok=True)
            raise KnowledgeConflictError("The failed document changed before retry")
        namespace = build_company_namespace(
            self.current_user.company_id, self.settings.pinecone_namespace_prefix
        )
        record_ids = self._record_ids(document)
        await self.session.rollback()
        await self.provider.delete(namespace, record_ids)
        document = await self.repository.get(document_id, for_update=True)
        if document is None or document.ingestion_status != KnowledgeIngestionStatus.FAILED:
            saved.path.unlink(missing_ok=True)
            raise KnowledgeConflictError("The failed document changed before retry")
        return await self._ingest_saved(document, saved)

    async def delete(self, document_id: UUID) -> None:
        await self._authorize_company()
        document = await self.repository.get(document_id, for_update=True)
        if document is None:
            return
        await authorize_document_management(
            self.current_user, document, self.department_repository
        )
        if document.status == KnowledgeDocumentStatus.DELETED:
            return
        namespace = build_company_namespace(
            self.current_user.company_id, self.settings.pinecone_namespace_prefix
        )
        record_ids = self._record_ids(document)
        await self.session.rollback()
        await self.provider.delete(namespace, record_ids)
        document = await self.repository.get(document_id, for_update=True)
        if document is not None and document.status != KnowledgeDocumentStatus.DELETED:
            await self.repository.mark_deleted(document)
            await self.session.commit()

    async def get(self, document_id: UUID) -> KnowledgeDocument:
        await self._authorize_company()
        document = await self.repository.get(document_id)
        if document is None:
            raise KnowledgeNotFoundError("Knowledge document not found")
        if self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            own = await trusted_manager_department(
                self.current_user, self.department_repository
            )
            if not set(document.department_scope).intersection(
                {own, KnowledgeDepartmentScope.SHARED}
            ):
                raise KnowledgeNotFoundError("Knowledge document not found")
        return document

    async def list(self, filters: KnowledgeDocumentListFilters):
        await self._authorize_company()
        visible = None
        if self.current_user.actor_type == ActorType.DEPARTMENT_MANAGER:
            own = await trusted_manager_department(
                self.current_user, self.department_repository
            )
            visible = [own, KnowledgeDepartmentScope.SHARED]
        return await self.repository.list(filters, visible_departments=visible)
