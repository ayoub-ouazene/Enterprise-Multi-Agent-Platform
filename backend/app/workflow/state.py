import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.json_validation import (
    EVENT_PROHIBITED_KEY_PARTS,
    validate_safe_json,
)
from app.requests.enums import RequestStatus
from app.core.enums import DepartmentType
from app.workflow.router_output import (
    RouterConfidence,
    RouterMessageCategory,
    RouterOutput,
)


STATE_VERSION = 1
WORKFLOW_STARTED_STEP = "workflow_started"
INITIALIZED_STEP = "initialized"
ROUTED_STEP = "router_routed"
LEGACY_ROUTED_STEP = "placeholder_routed"
DEPARTMENT_STARTED_STEP = "placeholder_department_started"
DEPARTMENT_COMPLETED_STEP = "placeholder_department_completed"
COMPLETED_STEP = "workflow_completed"

_JWT_PATTERN = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
_CREDENTIAL_URL_PATTERN = re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@", re.I)
_PRIVATE_KEY_MARKER = "-----BEGIN PRIVATE KEY-----"
_DATABASE_URL_PATTERN = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis)"
    r"(?:\+[a-z0-9_-]+)?://",
    re.I,
)


class WorkflowStateSection(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowRequestState(WorkflowStateSection):
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    request_type: str = Field(min_length=1, max_length=100)
    owner_department_id: UUID | None = None
    active_department_id: UUID | None = None
    status: RequestStatus = RequestStatus.CREATED
    current_stage: str = Field(default="request_received", min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=10_000)


class WorkflowPlanningState(WorkflowStateSection):
    initial_plan: list[str] = Field(default_factory=list, max_length=100)
    current_plan: list[str] = Field(default_factory=list, max_length=100)
    completed_steps: list[str] = Field(default_factory=list, max_length=200)
    pending_steps: list[str] = Field(default_factory=list, max_length=200)
    current_step: str | None = Field(default=None, max_length=255)
    plan_revision_count: int = Field(default=0, ge=0, le=1_000)


class WorkflowCollaborationState(WorkflowStateSection):
    sender_department_id: UUID | None = None
    receiver_department_id: UUID | None = None
    action: str | None = Field(default=None, max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class WorkflowExecutionState(WorkflowStateSection):
    tool_results: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    retrieval_references: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=200,
    )
    retry_counts: dict[str, int] = Field(default_factory=dict)
    last_operation: str | None = Field(default=None, max_length=255)
    last_operation_status: str | None = Field(default=None, max_length=100)


class WorkflowRoutingState(WorkflowStateSection):
    message_category: RouterMessageCategory | None = None
    selected_department: DepartmentType | None = None
    confidence: RouterConfidence | None = None
    needs_clarification: bool = False
    clarification_count: int = Field(default=0, ge=0, le=3)
    latest_question: str | None = Field(default=None, max_length=300)
    latest_answer: str | None = Field(default=None, max_length=10_000)
    routing_pending: bool = True
    request_type: str | None = Field(default=None, max_length=100)
    short_summary: str | None = Field(default=None, max_length=1_000)
    routing_reason: str | None = Field(default=None, max_length=500)
    unsupported_reason: str | None = Field(default=None, max_length=1_000)
    is_capability_gap: bool = False
    platform_answer: str | None = Field(default=None, max_length=2_000)


class WorkflowReviewState(WorkflowStateSection):
    required: bool = False
    status: str | None = Field(default=None, max_length=100)
    review_package: dict[str, Any] = Field(default_factory=dict)
    feedback: dict[str, Any] = Field(default_factory=dict)
    revision_completed: bool = False


class WorkflowHumanActionState(WorkflowStateSection):
    required: bool = False
    action_type: str | None = Field(default=None, max_length=100)
    assigned_user_id: UUID | None = None
    decision_package: dict[str, Any] = Field(default_factory=dict)
    status: str | None = Field(default=None, max_length=100)
    response: dict[str, Any] = Field(default_factory=dict)


class WorkflowFailureState(WorkflowStateSection):
    has_failure: bool = False
    failure_type: str | None = Field(default=None, max_length=100)
    safe_message: str | None = Field(default=None, max_length=2_000)
    failure_log_id: UUID | None = None
    alternative_attempted: bool = False
    terminal: bool = False


class WorkflowResultState(WorkflowStateSection):
    decision: str | None = Field(default=None, max_length=255)
    reason: str | None = Field(default=None, max_length=5_000)
    final_response: str | None = Field(default=None, max_length=10_000)
    completed_at: datetime | None = None


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_version: Literal[1] = STATE_VERSION
    request: WorkflowRequestState
    planning: WorkflowPlanningState = Field(default_factory=WorkflowPlanningState)
    collaboration: WorkflowCollaborationState = Field(
        default_factory=WorkflowCollaborationState
    )
    execution: WorkflowExecutionState = Field(default_factory=WorkflowExecutionState)
    routing: WorkflowRoutingState = Field(default_factory=WorkflowRoutingState)
    review: WorkflowReviewState = Field(default_factory=WorkflowReviewState)
    human_action: WorkflowHumanActionState = Field(
        default_factory=WorkflowHumanActionState
    )
    failure: WorkflowFailureState = Field(default_factory=WorkflowFailureState)
    result: WorkflowResultState = Field(default_factory=WorkflowResultState)

    @model_validator(mode="after")
    def validate_safe_serializable_state(self) -> "WorkflowState":
        storage = self.model_dump(mode="json")
        validate_safe_json(
            storage,
            path="workflow_state",
            forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS,
        )
        _reject_sensitive_string_values(storage)
        json.dumps(storage)
        return self

    def to_storage(self) -> dict[str, Any]:
        storage = self.model_dump(mode="json")
        json.dumps(storage)
        return storage


@dataclass(frozen=True, slots=True)
class DepartmentRuntimeContext:
    department_id: UUID
    is_active: bool


@dataclass(frozen=True, slots=True)
class WorkflowRuntimeContext:
    router_client: Any
    departments: dict[DepartmentType, DepartmentRuntimeContext]
    preclassified_output: RouterOutput | None = None


def _reject_sensitive_string_values(
    value: Any, *, path: str = "workflow_state"
) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _reject_sensitive_string_values(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_sensitive_string_values(nested, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if (
        _JWT_PATTERN.search(value)
        or _CREDENTIAL_URL_PATTERN.search(value)
        or _DATABASE_URL_PATTERN.search(value)
        or _PRIVATE_KEY_MARKER in value
    ):
        raise ValueError(f"{path} contains a prohibited secret-like value")


def build_initial_workflow_state(business_request: Any) -> WorkflowState:
    """Construct trusted initial state from a persisted Business Request."""

    return WorkflowState(
        request=WorkflowRequestState(
            request_id=business_request.id,
            company_id=business_request.company_id,
            requester_user_id=business_request.requester_user_id,
            requester_employee_id=business_request.requester_employee_id,
            request_type=business_request.request_type,
            owner_department_id=business_request.owner_department_id,
            active_department_id=business_request.active_department_id,
            status=business_request.status,
            current_stage=business_request.current_stage,
            summary=business_request.summary,
        )
    )


def add_completed_step(state: WorkflowState, step: str) -> WorkflowPlanningState:
    completed = list(state.planning.completed_steps)
    if step not in completed:
        completed.append(step)
    pending = [item for item in state.planning.pending_steps if item != step]
    return state.planning.model_copy(
        update={"completed_steps": completed, "pending_steps": pending}
    )


def apply_state_update(
    state: WorkflowState,
    update: dict[str, Any],
) -> WorkflowState:
    current = state.model_dump(mode="python")
    current.update(update)
    return WorkflowState.model_validate(current)
