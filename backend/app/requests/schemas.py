from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.json_validation import validate_safe_json
from app.requests.enums import RequestPriority, RequestStatus


class BusinessRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=10_000)
    priority: RequestPriority = RequestPriority.NORMAL
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_type", "title", "summary")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("custom_data")
    @classmethod
    def reject_sensitive_custom_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(value, path="custom_data")


class BusinessRequestMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = Field(default=None, min_length=1, max_length=10_000)
    priority: RequestPriority | None = None
    custom_data: dict[str, Any] | None = None

    @field_validator("title", "summary")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("custom_data")
    @classmethod
    def reject_sensitive_optional_custom_data(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return validate_safe_json(value, path="custom_data")


class BusinessRequestListFilters(BaseModel):
    status: RequestStatus | None = None
    priority: RequestPriority | None = None
    request_type: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class BusinessRequestSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_type: str
    title: str
    summary: str
    status: RequestStatus
    current_stage: str
    priority: RequestPriority
    owner_department_id: UUID | None
    active_department_id: UUID | None
    created_at: datetime
    updated_at: datetime


class BusinessRequestDetailResponse(BusinessRequestSummaryResponse):
    requester_user_id: UUID
    requester_employee_id: UUID | None
    final_decision: str | None
    final_reason: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    failed_at: datetime | None


class BusinessRequestCancellationResponse(BusinessRequestDetailResponse):
    pass
