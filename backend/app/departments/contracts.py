import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import ActorType, DepartmentType
from app.core.json_validation import EVENT_PROHIBITED_KEY_PARTS, validate_safe_json


_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,99}$")
_IDEMPOTENCY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PROHIBITED_TOOL_KEYS = (
    "command",
    "shell",
    "script",
    "python",
    "sql",
    "query",
    "url",
    "uri",
    "endpoint",
)
_PROHIBITED_EXECUTABLE_TEXT = re.compile(
    r"(?:https?://|\b(?:select|insert|update|delete|drop|alter)\b.+\b(?:from|into|table)\b|"
    r"\b(?:powershell|cmd\.exe|bash|sh\s+-c|python\s+-c)\b)",
    re.IGNORECASE,
)


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DepartmentExecutionStatus(StrEnum):
    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_TOOL = "waiting_for_tool"
    WAITING_FOR_DEPARTMENT = "waiting_for_department"
    WAITING_FOR_REVIEW = "waiting_for_review"
    WAITING_FOR_HUMAN = "waiting_for_human"
    WAITING_FOR_USER = "waiting_for_user"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class DepartmentNextAction(StrEnum):
    CONTINUE_DEPARTMENT = "continue_department"
    EXECUTE_TOOL = "execute_tool"
    COLLABORATE = "collaborate"
    REQUEST_REVIEW = "request_review"
    REQUEST_HUMAN_ACTION = "request_human_action"
    WAIT_FOR_USER_INPUT = "wait_for_user_input"
    COMPLETE_REQUEST = "complete_request"
    FAIL_REQUEST = "fail_request"


class DepartmentConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CollaborationStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


def _validate_safe_object(value: dict[str, Any], *, path: str) -> dict[str, Any]:
    validate_safe_json(
        value,
        path=path,
        forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS,
    )
    return value


def _validate_identifier(value: str) -> str:
    normalized = value.strip()
    if not _IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError("must be a normalized lowercase identifier")
    return normalized


class DepartmentCollaborationRequest(StrictContract):
    request_id: UUID
    sender_department: DepartmentType
    receiver_department: DepartmentType
    action: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    expected_output: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        return _validate_identifier(value)

    @field_validator("payload", "expected_output")
    @classmethod
    def validate_objects(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_safe_object(value, path="collaboration")

    @model_validator(mode="after")
    def validate_departments(self) -> "DepartmentCollaborationRequest":
        if self.sender_department == self.receiver_department:
            raise ValueError("collaboration departments must differ")
        return self


class DepartmentCollaborationResult(StrictContract):
    request_id: UUID
    sender_department: DepartmentType
    receiver_department: DepartmentType
    action: str = Field(min_length=1, max_length=100)
    status: CollaborationStatus
    result: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=2_000)

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        return _validate_identifier(value)

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_safe_object(value, path="collaboration_result")

    @model_validator(mode="after")
    def validate_departments(self) -> "DepartmentCollaborationResult":
        if self.sender_department == self.receiver_department:
            raise ValueError("collaboration departments must differ")
        return self


class DepartmentToolRequest(StrictContract):
    tool_name: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=2_000)
    idempotency_key: str | None = Field(default=None, max_length=128)
    expected_result_type: str = Field(min_length=1, max_length=100)

    @field_validator("tool_name", "operation", "expected_result_type")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        return _validate_identifier(value)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not _IDEMPOTENCY_PATTERN.fullmatch(normalized):
            raise ValueError("contains unsupported characters")
        return normalized

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, value: dict[str, Any]) -> dict[str, Any]:
        _validate_safe_object(value, path="tool_arguments")

        def reject_executable_content(item: Any) -> None:
            if isinstance(item, dict):
                for key, nested in item.items():
                    normalized_key = str(key).casefold()
                    if any(part in normalized_key for part in _PROHIBITED_TOOL_KEYS):
                        raise ValueError("tool arguments contain an executable field")
                    reject_executable_content(nested)
            elif isinstance(item, list):
                for nested in item:
                    reject_executable_content(nested)
            elif isinstance(item, str) and _PROHIBITED_EXECUTABLE_TEXT.search(item):
                raise ValueError("tool arguments contain executable content")

        reject_executable_content(value)
        return value


class DepartmentReviewPackage(StrictContract):
    request_summary: str = Field(min_length=1, max_length=2_000)
    proposed_decision: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2_000)
    policy_references: list[str] = Field(default_factory=list, max_length=100)
    evidence_references: list[str] = Field(default_factory=list, max_length=100)
    tool_result_summaries: list[str] = Field(default_factory=list, max_length=100)
    checked_constraints: list[str] = Field(default_factory=list, max_length=100)
    required_approvals: list[str] = Field(default_factory=list, max_length=50)
    confidence: DepartmentConfidence


class ReviewFeedbackContext(StrictContract):
    status: str = Field(min_length=1, max_length=100)
    feedback: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(min_length=1, max_length=2_000)


class DepartmentHumanActionRequest(StrictContract):
    action_type: str = Field(min_length=1, max_length=100)
    assigned_role: ActorType | None = None
    assigned_user_id: UUID | None = None
    request_summary: str = Field(min_length=1, max_length=2_000)
    evidence_summary: str = Field(min_length=1, max_length=2_000)
    recommendation: str = Field(min_length=1, max_length=2_000)
    exact_action_required: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(min_length=1, max_length=2_000)
    due_date: datetime | None = None
    rejection_or_timeout_consequence: str | None = Field(
        default=None,
        max_length=2_000,
    )

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, value: str) -> str:
        return _validate_identifier(value)

    @model_validator(mode="after")
    def validate_assignment(self) -> "DepartmentHumanActionRequest":
        if self.assigned_role is None and self.assigned_user_id is None:
            raise ValueError("a human action must have a role or user assignee")
        return self


class HumanResponseContext(StrictContract):
    action_type: str = Field(min_length=1, max_length=100)
    responding_user_id: UUID
    decision: str = Field(min_length=1, max_length=100)
    response: str = Field(min_length=1, max_length=2_000)
    responded_at: datetime


class DepartmentPlanningUpdates(StrictContract):
    current_plan: list[str] | None = Field(default=None, max_length=100)
    pending_steps: list[str] | None = Field(default=None, max_length=200)
    current_step: str | None = Field(default=None, max_length=255)


class DepartmentExecutionUpdates(StrictContract):
    last_operation: str | None = Field(default=None, max_length=255)
    last_operation_status: str | None = Field(default=None, max_length=100)
    retry_counts: dict[str, int] | None = None
    department_data: dict[str, Any] | None = None

    @field_validator("department_data")
    @classmethod
    def validate_department_data(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            return _validate_safe_object(value, path="department_data")
        return value


class DepartmentRoutingUpdates(StrictContract):
    needs_clarification: bool | None = None
    latest_question: str | None = Field(default=None, max_length=300)
    routing_pending: bool | None = None


class DepartmentCollaborationUpdates(StrictContract):
    request: DepartmentCollaborationRequest | None = None
    result: DepartmentCollaborationResult | None = None
    is_active: bool = False


class DepartmentReviewUpdates(StrictContract):
    required: bool | None = None
    status: str | None = Field(default=None, max_length=100)
    review_package: DepartmentReviewPackage | None = None
    feedback: ReviewFeedbackContext | None = None


class DepartmentHumanActionUpdates(StrictContract):
    required: bool | None = None
    request: DepartmentHumanActionRequest | None = None
    response: HumanResponseContext | None = None


class DepartmentResultUpdates(StrictContract):
    decision: str | None = Field(default=None, max_length=255)
    reason: str | None = Field(default=None, max_length=5_000)
    final_response: str | None = Field(default=None, max_length=10_000)


class DepartmentStateUpdates(StrictContract):
    current_stage: str | None = Field(default=None, max_length=100)
    planning: DepartmentPlanningUpdates | None = None
    execution: DepartmentExecutionUpdates | None = None
    routing: DepartmentRoutingUpdates | None = None
    collaboration: DepartmentCollaborationUpdates | None = None
    review: DepartmentReviewUpdates | None = None
    human_action: DepartmentHumanActionUpdates | None = None
    result: DepartmentResultUpdates | None = None


class DepartmentExecutionContext(StrictContract):
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    requester_department_id: UUID | None = None
    requester_actor_type: ActorType = ActorType.EXTERNAL_USER
    requester_is_manager: bool = False
    owner_department_type: DepartmentType
    active_department_type: DepartmentType
    request_type: str = Field(min_length=1, max_length=100)
    request_summary: str = Field(min_length=1, max_length=10_000)
    current_stage: str = Field(min_length=1, max_length=100)
    current_plan: list[str] = Field(default_factory=list, max_length=100)
    completed_steps: list[str] = Field(default_factory=list, max_length=200)
    pending_steps: list[str] = Field(default_factory=list, max_length=200)
    relevant_custom_data: dict[str, Any] = Field(default_factory=dict)
    latest_user_input: str | None = Field(default=None, max_length=10_000)
    collaboration_input: DepartmentCollaborationRequest | None = None
    collaboration_result: DepartmentCollaborationResult | None = None
    review_feedback: ReviewFeedbackContext | None = None
    human_response: HumanResponseContext | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    department_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relevant_custom_data", "department_data")
    @classmethod
    def validate_custom_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _validate_safe_object(value, path="relevant_custom_data")

    @field_validator("tool_results")
    @classmethod
    def validate_tool_results(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in value:
            _validate_safe_object(item, path="tool_results")
        return value


class DepartmentExecutionResult(StrictContract):
    department_type: DepartmentType
    status: DepartmentExecutionStatus
    decision: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2_000)
    user_message: str = Field(min_length=1, max_length=2_000)
    current_stage: str = Field(min_length=1, max_length=100)
    completed_step: str = Field(min_length=1, max_length=100)
    next_action: DepartmentNextAction
    next_department: DepartmentType | None = None
    requires_tool: bool = False
    tool_request: DepartmentToolRequest | None = None
    requires_collaboration: bool = False
    collaboration_request: DepartmentCollaborationRequest | None = None
    requires_review: bool = False
    review_package: DepartmentReviewPackage | None = None
    requires_human_action: bool = False
    human_action_request: DepartmentHumanActionRequest | None = None
    is_terminal: bool
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2_000)
    state_updates: DepartmentStateUpdates = Field(
        default_factory=DepartmentStateUpdates
    )

    @field_validator("completed_step")
    @classmethod
    def validate_completed_step(cls, value: str) -> str:
        return _validate_identifier(value)

    @model_validator(mode="after")
    def validate_next_action(self) -> "DepartmentExecutionResult":
        expected = {
            DepartmentNextAction.CONTINUE_DEPARTMENT: (
                DepartmentExecutionStatus.IN_PROGRESS,
                False,
                False,
                False,
                False,
                False,
            ),
            DepartmentNextAction.EXECUTE_TOOL: (
                DepartmentExecutionStatus.WAITING_FOR_TOOL,
                True,
                False,
                False,
                False,
                False,
            ),
            DepartmentNextAction.COLLABORATE: (
                DepartmentExecutionStatus.WAITING_FOR_DEPARTMENT,
                False,
                True,
                False,
                False,
                False,
            ),
            DepartmentNextAction.REQUEST_REVIEW: (
                DepartmentExecutionStatus.WAITING_FOR_REVIEW,
                False,
                False,
                True,
                False,
                False,
            ),
            DepartmentNextAction.REQUEST_HUMAN_ACTION: (
                DepartmentExecutionStatus.WAITING_FOR_HUMAN,
                False,
                False,
                False,
                True,
                False,
            ),
            DepartmentNextAction.WAIT_FOR_USER_INPUT: (
                DepartmentExecutionStatus.WAITING_FOR_USER,
                False,
                False,
                False,
                False,
                False,
            ),
            DepartmentNextAction.COMPLETE_REQUEST: (
                DepartmentExecutionStatus.COMPLETED,
                False,
                False,
                False,
                False,
                True,
            ),
        }
        if self.next_action == DepartmentNextAction.FAIL_REQUEST:
            if self.status not in {
                DepartmentExecutionStatus.FAILED,
                DepartmentExecutionStatus.UNSUPPORTED,
            } or not self.is_terminal:
                raise ValueError("fail_request requires a terminal failure status")
            flags = (
                self.requires_tool,
                self.requires_collaboration,
                self.requires_review,
                self.requires_human_action,
            )
            if any(flags):
                raise ValueError("fail_request cannot require another action")
        else:
            status, tool, collaboration, review, human, terminal = expected[
                self.next_action
            ]
            if (
                self.status != status
                or self.requires_tool != tool
                or self.requires_collaboration != collaboration
                or self.requires_review != review
                or self.requires_human_action != human
                or self.is_terminal != terminal
            ):
                raise ValueError("department next-action fields are contradictory")

        payload_checks = (
            (self.requires_tool, self.tool_request, "tool_request"),
            (
                self.requires_collaboration,
                self.collaboration_request,
                "collaboration_request",
            ),
            (self.requires_review, self.review_package, "review_package"),
            (
                self.requires_human_action,
                self.human_action_request,
                "human_action_request",
            ),
        )
        for required, payload, name in payload_checks:
            if required != (payload is not None):
                raise ValueError(f"{name} does not match its requirement flag")

        if self.requires_collaboration:
            collaboration = self.collaboration_request
            if (
                collaboration is None
                or self.next_department != collaboration.receiver_department
                or collaboration.sender_department != self.department_type
            ):
                raise ValueError("collaboration routing is inconsistent")
        elif self.next_department is not None:
            raise ValueError("next_department is allowed only for collaboration")
        return self
