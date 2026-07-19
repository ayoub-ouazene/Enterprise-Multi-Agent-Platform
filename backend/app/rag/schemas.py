from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.json_validation import validate_safe_json
from app.rag.enums import (
    KnowledgeAccessScope,
    KnowledgeDepartmentScope,
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
)


class KnowledgeDocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    department_scope: list[KnowledgeDepartmentScope] = Field(min_length=1, max_length=5)
    access_scope: KnowledgeAccessScope
    effective_date: date | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("department_scope")
    @classmethod
    def validate_departments(
        cls, value: list[KnowledgeDepartmentScope]
    ) -> list[KnowledgeDepartmentScope]:
        unique = list(dict.fromkeys(value))
        if KnowledgeDepartmentScope.SHARED in unique and len(unique) != 1:
            raise ValueError("shared scope cannot be combined with departments")
        return unique

    @field_validator("custom_metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        safe = validate_safe_json(value, path="custom_metadata")
        if len(str(safe).encode("utf-8")) > 8192:
            raise ValueError("custom_metadata is too large")
        return safe


class KnowledgeDocumentListFilters(BaseModel):
    document_type: KnowledgeDocumentType | None = None
    status: KnowledgeDocumentStatus | None = None
    ingestion_status: KnowledgeIngestionStatus | None = None
    department: KnowledgeDepartmentScope | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    document_type: KnowledgeDocumentType
    department_scope: list[KnowledgeDepartmentScope]
    access_scope: KnowledgeAccessScope
    version: int
    status: KnowledgeDocumentStatus
    is_active: bool
    effective_date: date | None
    supersedes_document_id: UUID | None
    mime_type: str
    file_size_bytes: int
    chunk_count: int
    ingestion_status: KnowledgeIngestionStatus
    ingestion_error_safe: str | None
    custom_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    ingested_at: datetime | None
    deleted_at: datetime | None


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_text: str = Field(min_length=1, max_length=2000)
    department: KnowledgeDepartmentScope | None = None
    document_types: list[KnowledgeDocumentType] | None = Field(
        default=None, min_length=1, max_length=9
    )
    top_k: int | None = Field(default=None, ge=1)
    effective_at: date | None = None

    @field_validator("query_text")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class KnowledgeRetrievalQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: UUID
    query_text: str
    departments: list[KnowledgeDepartmentScope]
    allowed_access_scopes: list[KnowledgeAccessScope]
    document_types: list[KnowledgeDocumentType] | None = None
    top_k: int
    active_only: bool = True
    effective_at: date | None = None

    @model_validator(mode="after")
    def nonempty_trusted_filters(self) -> "KnowledgeRetrievalQuery":
        if not self.departments or not self.allowed_access_scopes:
            raise ValueError("Trusted retrieval filters must not be empty")
        return self


class KnowledgeChunkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    document_id: UUID
    title: str
    document_type: KnowledgeDocumentType
    department_scope: list[KnowledgeDepartmentScope]
    access_scope: KnowledgeAccessScope
    version: int
    chunk_index: int
    chunk_text: str
    similarity_score: float
    source_filename: str
    effective_date: date | None


class ExtractedDocument(BaseModel):
    text: str
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class TextChunk(BaseModel):
    index: int
    text: str
