from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DepartmentType


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    department_type: DepartmentType
    is_active: bool = True
    custom_data: dict[str, Any] = Field(default_factory=dict)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    department_type: DepartmentType | None = None
    is_active: bool | None = None
    custom_data: dict[str, Any] | None = None


class DepartmentInternalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    department_type: DepartmentType
    is_active: bool
    custom_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    department_type: DepartmentType
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DepartmentStatsResponse(BaseModel):
    """High-level stats for a department workspace overview."""

    model_config = ConfigDict(extra="forbid")

    active_requests: int = 0
    pending_human_actions: int = 0
    collaborations_ongoing: int = 0
    completed_today: int = 0


class DepartmentReadinessItem(BaseModel):
    """One readiness check for a department workspace."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ready: bool
    detail: str | None = None


class DepartmentReadinessResponse(BaseModel):
    """Department readiness summary."""

    model_config = ConfigDict(extra="forbid")

    department_type: DepartmentType
    overall_ready: bool
    items: list[DepartmentReadinessItem]


class DepartmentActivityResponse(BaseModel):
    """Recent activity for a department workspace."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID
    event_type: str
    title: str
    message: str
    actor_label: str
    created_at: datetime


class DepartmentOperationalField(BaseModel):
    """One allowlisted display value in a department operational record."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)
    emphasis: Literal["default", "positive", "warning", "critical"] = "default"


class DepartmentOperationalRecordResponse(BaseModel):
    """Safe common projection over department extension records."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    request_id: UUID | None = None
    record_type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=1000)
    status: str = Field(min_length=1, max_length=100)
    fields: list[DepartmentOperationalField] = Field(default_factory=list, max_length=12)
    action_url: str | None = Field(default=None, max_length=500)
    updated_at: datetime | None = None
