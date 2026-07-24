from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


HumanActionStatus = Literal["pending", "resolved", "cancelled"]


class HumanActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    action_type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10_000)
    assigned_user_id: UUID | None = None
    assigned_role: str | None = Field(default=None, max_length=50)
    decision_package: dict[str, Any] = Field(default_factory=dict)
    due_date: datetime | None = None

    @field_validator("action_type", "title", "assigned_role")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HumanActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID
    action_type: str
    title: str
    description: str
    status: str
    assigned_user_id: UUID | None
    assigned_role: str | None
    decision_package: dict[str, Any]
    response: dict[str, Any]
    due_date: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HumanActionListFilters(BaseModel):
    status: HumanActionStatus | None = None
    request_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class HumanActionSubmitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: str
    resolved_at: datetime | None


class HumanActionSubmitPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(min_length=1, max_length=100)
    response: str = Field(min_length=1, max_length=10_000)

    @field_validator("decision", "response")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped
