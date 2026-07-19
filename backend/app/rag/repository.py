from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.enums import (
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)
from app.rag.models import KnowledgeDocument
from app.rag.schemas import KnowledgeDocumentListFilters, KnowledgeDocumentMetadata


class KnowledgeDocumentRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    def _tenant_statement(self):
        return select(KnowledgeDocument).where(
            KnowledgeDocument.company_id == self.company_id
        )

    async def create_pending(
        self,
        *,
        uploaded_by_user_id: UUID,
        metadata: KnowledgeDocumentMetadata,
        original_filename: str,
        mime_type: str,
        file_size_bytes: int,
        checksum: str,
        version: int = 1,
        supersedes_document_id: UUID | None = None,
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            company_id=self.company_id,
            uploaded_by_user_id=uploaded_by_user_id,
            title=metadata.title,
            original_filename=original_filename,
            stored_filename=None,
            document_type=metadata.document_type,
            department_scope=metadata.department_scope,
            access_scope=metadata.access_scope,
            version=version,
            status=KnowledgeDocumentStatus.DRAFT,
            is_active=False,
            effective_date=metadata.effective_date,
            supersedes_document_id=supersedes_document_id,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            checksum=checksum,
            chunk_count=0,
            ingestion_status=KnowledgeIngestionStatus.PENDING,
            custom_metadata=metadata.custom_metadata,
        )
        self.session.add(document)
        await self.session.flush()
        return document

    async def get(self, document_id: UUID, *, for_update: bool = False):
        statement = self._tenant_statement().where(KnowledgeDocument.id == document_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list(
        self,
        filters: KnowledgeDocumentListFilters,
        *,
        visible_departments: list[KnowledgeDepartmentScope] | None = None,
    ):
        statement = self._tenant_statement()
        if visible_departments is not None:
            statement = statement.where(
                KnowledgeDocument.department_scope.overlap(visible_departments)
            )
        if filters.document_type is not None:
            statement = statement.where(
                KnowledgeDocument.document_type == filters.document_type
            )
        if filters.status is not None:
            statement = statement.where(KnowledgeDocument.status == filters.status)
        if filters.ingestion_status is not None:
            statement = statement.where(
                KnowledgeDocument.ingestion_status == filters.ingestion_status
            )
        if filters.department is not None:
            statement = statement.where(
                KnowledgeDocument.department_scope.overlap([filters.department])
            )
        result = await self.session.scalars(
            statement.order_by(
                KnowledgeDocument.created_at.desc(), KnowledgeDocument.id.desc()
            )
            .offset(filters.offset)
            .limit(filters.limit)
        )
        return list(result.all())

    async def find_active_duplicate(self, checksum: str):
        return await self.session.scalar(
            self._tenant_statement().where(
                KnowledgeDocument.checksum == checksum,
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.ingestion_status
                == KnowledgeIngestionStatus.COMPLETED,
            )
        )

    async def active_by_ids(self, document_ids: set[UUID]):
        if not document_ids:
            return {}
        result = await self.session.scalars(
            self._tenant_statement().where(
                KnowledgeDocument.id.in_(document_ids),
                KnowledgeDocument.is_active.is_(True),
                KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE,
                KnowledgeDocument.ingestion_status
                == KnowledgeIngestionStatus.COMPLETED,
            )
        )
        return {document.id: document for document in result.all()}

    async def mark_processing(self, document: KnowledgeDocument) -> None:
        document.ingestion_status = KnowledgeIngestionStatus.PROCESSING
        document.ingestion_error_safe = None
        await self.session.flush()

    async def mark_completed(
        self, document: KnowledgeDocument, chunk_count: int
    ) -> None:
        document.status = KnowledgeDocumentStatus.ACTIVE
        document.is_active = True
        document.ingestion_status = KnowledgeIngestionStatus.COMPLETED
        document.ingestion_error_safe = None
        document.chunk_count = chunk_count
        document.ingested_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, document: KnowledgeDocument, safe_error: str) -> None:
        document.status = KnowledgeDocumentStatus.DRAFT
        document.is_active = False
        document.ingestion_status = KnowledgeIngestionStatus.FAILED
        document.ingestion_error_safe = safe_error[:2000]
        await self.session.flush()

    async def mark_superseded(self, document: KnowledgeDocument) -> None:
        document.status = KnowledgeDocumentStatus.SUPERSEDED
        document.is_active = False
        await self.session.flush()

    async def mark_deleted(self, document: KnowledgeDocument) -> None:
        document.status = KnowledgeDocumentStatus.DELETED
        document.is_active = False
        document.deleted_at = datetime.now(UTC)
        await self.session.flush()
