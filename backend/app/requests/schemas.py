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
    search: str | None = Field(default=None, min_length=1, max_length=200)
    owner_department_id: UUID | None = None
    requester_user_id: UUID | None = None
    attention_required: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RequestDepartmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    department_type: str


class ConnectedHumanActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    title: str
    action_type: str
    status: str
    due_at: datetime | None
    assigned_role: str | None
    can_respond: bool
    action_url: str | None


class RequestClarificationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    number: int = Field(ge=1, le=3)
    maximum: int = 3


class RequestSourceReferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID | None = None
    title: str
    version: str | None = None
    section: str | None = None
    scope: str | None = None


class RequestFinalResultResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    summary: str
    limitations: list[str] = Field(default_factory=list, max_length=20)
    next_steps: list[str] = Field(default_factory=list, max_length=20)
    sources: list[RequestSourceReferenceResponse] = Field(
        default_factory=list,
        max_length=20,
    )


class BusinessRequestSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_type: str
    title: str
    summary: str
    status: RequestStatus
    current_stage: str
    current_state_summary: str
    priority: RequestPriority
    owner_department_id: UUID | None
    active_department_id: UUID | None
    owner_department: RequestDepartmentResponse | None = None
    active_department: RequestDepartmentResponse | None = None
    requester_user_id: UUID | None = None
    requester_label: str | None = None
    attention_required: bool = False
    pending_action_count: int = 0
    can_cancel: bool = False
    created_at: datetime
    updated_at: datetime


class BusinessRequestDetailResponse(BusinessRequestSummaryResponse):
    requester_employee_id: UUID | None
    final_decision: str | None
    final_reason: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    failed_at: datetime | None
    clarification: RequestClarificationResponse | None = None
    collaboration_summary: str | None = None
    quality_check_summary: str | None = None
    failure_summary: str | None = None
    final_result: RequestFinalResultResponse | None = None
    connected_actions: list[ConnectedHumanActionResponse] = Field(
        default_factory=list,
        max_length=50,
    )
    allowed_actions: list[str] = Field(default_factory=list)


class BusinessRequestCancellationResponse(BusinessRequestDetailResponse):
    pass
