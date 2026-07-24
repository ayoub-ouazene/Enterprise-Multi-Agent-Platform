from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.json_validation import (
    EVENT_PROHIBITED_KEY_PARTS,
    validate_safe_json,
)
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.requests.enums import RequestStatus
from app.core.enums import DepartmentType
from app.workflow.router_output import RouterMessageCategory


class WorkflowEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: WorkflowEventType
    stage: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10_000)
    actor_type: WorkflowEventActorType
    department_id: UUID | None = None
    visibility: WorkflowEventVisibility
    event_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stage", "title", "message")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("event_data")
    @classmethod
    def reject_prohibited_event_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(
            value,
            path="event_data",
            forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS,
        )


class WorkflowEventPublicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID
    event_type: WorkflowEventType
    stage: str | None
    title: str
    message: str
    actor_label: str
    department_id: UUID | None
    event_data: dict[str, Any]
    sequence_number: int
    created_at: datetime


class WorkflowClarifyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=10_000)

    @field_validator("answer")
    @classmethod
    def strip_answer(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class WorkflowControlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    status: RequestStatus
    current_stage: str
    owner_department_id: UUID | None
    active_department_id: UUID | None
    state_version: int
    message_category: RouterMessageCategory | None = None
    owner_department: DepartmentType | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    response: str | None = None
