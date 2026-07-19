from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import enum_values
from app.database.base import Base
from app.database.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.rag.enums import (
    KnowledgeAccessScope,
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)

if TYPE_CHECKING:
    from app.companies.models import Company
    from app.users.models import User


class KnowledgeDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_knowledge_documents_positive_version"),
        CheckConstraint(
            "file_size_bytes > 0", name="ck_knowledge_documents_positive_file_size"
        ),
        CheckConstraint(
            "chunk_count >= 0", name="ck_knowledge_documents_nonnegative_chunks"
        ),
        CheckConstraint(
            "cardinality(department_scope) > 0",
            name="ck_knowledge_documents_department_scope_nonempty",
        ),
        CheckConstraint(
            "NOT is_active OR (status = 'active' AND ingestion_status = 'completed')",
            name="ck_knowledge_documents_active_completed",
        ),
        UniqueConstraint(
            "supersedes_document_id",
            name="uq_knowledge_documents_supersedes",
        ),
        Index("ix_knowledge_documents_company_status", "company_id", "status"),
        Index("ix_knowledge_documents_company_active", "company_id", "is_active"),
        Index(
            "ix_knowledge_documents_company_ingestion",
            "company_id",
            "ingestion_status",
        ),
        Index("ix_knowledge_documents_company_checksum", "company_id", "checksum"),
        Index("ix_knowledge_documents_company_type", "company_id", "document_type"),
    )

    company_id: Mapped[UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_type: Mapped[KnowledgeDocumentType] = mapped_column(
        SAEnum(
            KnowledgeDocumentType,
            name="knowledge_document_type",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    department_scope: Mapped[list[KnowledgeDepartmentScope]] = mapped_column(
        ARRAY(
            SAEnum(
                KnowledgeDepartmentScope,
                name="knowledge_department_scope",
                values_callable=enum_values,
                validate_strings=True,
            )
        ),
        nullable=False,
    )
    access_scope: Mapped[KnowledgeAccessScope] = mapped_column(
        SAEnum(
            KnowledgeAccessScope,
            name="knowledge_access_scope",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[KnowledgeDocumentStatus] = mapped_column(
        SAEnum(
            KnowledgeDocumentStatus,
            name="knowledge_document_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=KnowledgeDocumentStatus.DRAFT,
        server_default=KnowledgeDocumentStatus.DRAFT.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supersedes_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("knowledge_documents.id", ondelete="SET NULL"), nullable=True
    )
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    ingestion_status: Mapped[KnowledgeIngestionStatus] = mapped_column(
        SAEnum(
            KnowledgeIngestionStatus,
            name="knowledge_ingestion_status",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=KnowledgeIngestionStatus.PENDING,
        server_default=KnowledgeIngestionStatus.PENDING.value,
    )
    ingestion_error_safe: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    ingested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    company: Mapped["Company"] = relationship(foreign_keys=[company_id], lazy="raise")
    uploader: Mapped["User"] = relationship(
        foreign_keys=[uploaded_by_user_id], lazy="raise"
    )
    supersedes: Mapped["KnowledgeDocument | None"] = relationship(
        remote_side="KnowledgeDocument.id",
        foreign_keys=[supersedes_document_id],
        lazy="raise",
    )
