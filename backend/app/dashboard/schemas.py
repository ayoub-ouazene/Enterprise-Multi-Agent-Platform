from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardMetric(BaseModel):
    key: str
    label: str
    value: int
    detail: str | None = None
    status: str = "neutral"
    href: str | None = None


class DashboardAttentionItem(BaseModel):
    id: str
    severity: str
    title: str
    explanation: str
    resource_type: str
    resource_id: UUID | None = None
    action_label: str
    action_url: str
    occurred_at: datetime | None = None
    due_at: datetime | None = None


class DashboardRequestItem(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    current_stage: str
    owner_department: str | None
    action_required: bool
    updated_at: datetime


class DashboardActionItem(BaseModel):
    id: UUID
    request_id: UUID
    title: str
    action_type: str
    due_at: datetime | None
    created_at: datetime


class DashboardActivityItem(BaseModel):
    id: UUID
    title: str
    message: str
    severity: str
    resource_url: str | None
    occurred_at: datetime


class DashboardReadinessItem(BaseModel):
    key: str
    label: str
    ready: bool
    detail: str | None = None


class DashboardDepartmentItem(BaseModel):
    id: UUID
    name: str
    department_type: str
    enabled: bool
    manager_label: str | None
    ready: bool
    active_requests: int
    pending_actions: int


class DashboardIdentity(BaseModel):
    company_name: str
    company_active: bool
    account_label: str
    department_name: str | None = None
    department_type: str | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str
    identity: DashboardIdentity
    metrics: list[DashboardMetric]
    attention: list[DashboardAttentionItem] = Field(max_length=8)
    active_requests: list[DashboardRequestItem] = Field(max_length=6)
    completed_requests: list[DashboardRequestItem] = Field(max_length=5)
    pending_actions: list[DashboardActionItem] = Field(max_length=6)
    activity: list[DashboardActivityItem] = Field(max_length=8)
    readiness: list[DashboardReadinessItem] = Field(default_factory=list)
    departments: list[DashboardDepartmentItem] = Field(default_factory=list)
    generated_at: datetime
