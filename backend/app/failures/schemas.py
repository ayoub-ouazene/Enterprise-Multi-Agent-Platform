from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.json_validation import EVENT_PROHIBITED_KEY_PARTS, validate_safe_json
from app.core.sanitization import sanitize_internal_message, sanitize_safe_message
from app.failures.enums import CapabilityGapStatus, FailureSource, FailureType


class FailureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID | None = None
    department_id: UUID | None = None
    failure_type: FailureType
    failure_source: FailureSource
    failed_operation: str = Field(min_length=1, max_length=255)
    internal_message: str = Field(min_length=1, max_length=20_000)
    safe_message: str = Field(min_length=1, max_length=2_000)
    error_code: str | None = Field(default=None, max_length=100)
    technical_data: dict[str, Any] = Field(default_factory=dict)
    alternative_attempted: bool = False
    alternative_description: str | None = Field(default=None, max_length=5_000)
    is_terminal: bool = False

    @field_validator("failed_operation", "error_code")
    @classmethod
    def strip_short_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("internal_message", "alternative_description")
    @classmethod
    def sanitize_internal_text(cls, value: str | None) -> str | None:
        return None if value is None else sanitize_internal_message(value)

    @field_validator("safe_message")
    @classmethod
    def sanitize_public_text(cls, value: str) -> str:
        return sanitize_safe_message(value)

    @field_validator("technical_data")
    @classmethod
    def validate_diagnostics(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(
            value, path="technical_data", forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS
        )


class SafeFailureResponse(BaseModel):
    id: UUID
    request_id: UUID | None
    safe_message: str
    is_terminal: bool
    created_at: datetime


class FailureDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID | None
    department_id: UUID | None
    failure_type: FailureType
    failure_source: FailureSource
    failed_operation: str
    internal_message: str
    safe_message: str
    error_code: str | None
    technical_data: dict[str, Any]
    alternative_attempted: bool
    alternative_description: str | None
    is_terminal: bool
    resolved: bool
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    created_at: datetime


class FailureListFilters(BaseModel):
    failure_type: FailureType | None = None
    failure_source: FailureSource | None = None
    resolved: bool | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CapabilityGapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID | None = None
    department_id: UUID | None = None
    requested_operation: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10_000)
    safe_user_message: str = Field(min_length=1, max_length=2_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requested_operation")
    @classmethod
    def strip_operation(cls, value: str) -> str:
        return value.strip()

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, value: str) -> str:
        return sanitize_internal_message(value)

    @field_validator("safe_user_message")
    @classmethod
    def sanitize_user_message(cls, value: str) -> str:
        return sanitize_safe_message(value)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(
            value, path="metadata", forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS
        )


class CapabilityGapSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID | None
    department_id: UUID | None
    requested_operation: str
    status: CapabilityGapStatus
    occurrence_count: int
    first_seen_at: datetime
    last_seen_at: datetime


class CapabilityGapDetailResponse(CapabilityGapSummaryResponse):
    description: str
    safe_user_message: str
    resolved_at: datetime | None
    resolved_by_user_id: UUID | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime


class CapabilityGapStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CapabilityGapStatus
    resolution_notes: str | None = Field(default=None, max_length=5_000)

    @field_validator("resolution_notes")
    @classmethod
    def sanitize_notes(cls, value: str | None) -> str | None:
        return None if value is None else sanitize_internal_message(value)


class CapabilityGapListFilters(BaseModel):
    status: CapabilityGapStatus | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
