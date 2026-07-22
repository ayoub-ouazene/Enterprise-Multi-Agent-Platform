from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.onboarding.enums import ImportJobStatus, ImportType


# ---------------------------------------------------------------------------
# Import job schemas
# ---------------------------------------------------------------------------


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    import_type: ImportType
    status: ImportJobStatus
    original_filename: str
    uploaded_by_user_id: UUID
    total_rows: int
    valid_rows: int
    invalid_rows: int
    processed_rows: int
    error_summary: str | None
    checksum: str
    idempotency_key: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None


class ImportJobListFilters(BaseModel):
    import_type: ImportType | None = None
    status: ImportJobStatus | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Validation / confirmation
# ---------------------------------------------------------------------------


class RowValidationResult(BaseModel):
    row_number: int
    status: str  # "valid" | "invalid"
    errors: list[str] = Field(default_factory=list)
    preview: dict[str, Any] | None = None


class ImportValidateResponse(BaseModel):
    import_job_id: UUID
    import_type: ImportType
    total_rows: int
    valid_rows: int
    invalid_rows: int
    can_confirm: bool
    rows: list[RowValidationResult]


class ImportConfirmResponse(BaseModel):
    import_job_id: UUID
    status: ImportJobStatus
    processed_rows: int
    errors: list[str] | None = None


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------


class TemplateColumn(BaseModel):
    name: str
    required: bool
    description: str | None = None


class ImportTemplateResponse(BaseModel):
    import_type: ImportType
    columns: list[TemplateColumn]
    csv_header: str


# ---------------------------------------------------------------------------
# Onboarding status / activation
# ---------------------------------------------------------------------------


class OnboardingStatusItem(BaseModel):
    requirement: str
    satisfied: bool
    details: str | None = None


class OnboardingStatusResponse(BaseModel):
    company_id: UUID
    can_activate: bool
    is_active: bool
    items: list[OnboardingStatusItem]


class OnboardingActivateResponse(BaseModel):
    company_id: UUID
    activated: bool
    message: str
