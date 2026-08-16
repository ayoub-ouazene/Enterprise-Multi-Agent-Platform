"""Simplified workflow state for the linear checkpoint engine.

Removes the heavy Pydantic validators that ran ``json.dumps`` on every
state update.  Each section is a plain ``TypedDict``; the top-level
``WorkflowState`` is frozen after construction and updated via
``replace()`` (similar to ``functools.partial`` but for dicts).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.core.enums import DepartmentType
from app.requests.enums import RequestStatus
from app.workflow.router_output import RouterMessageCategory


class RoutingStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_TOOL = "needs_tool"
    NEEDS_COLLABORATION = "needs_collaboration"
    NEEDS_REVIEW = "needs_review"
    NEEDS_HUMAN = "needs_human"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RequestSection:
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    request_type: str = ""
    owner_department_id: UUID | None = None
    owner_department_type: DepartmentType | None = None
    active_department_id: UUID | None = None
    active_department_type: DepartmentType | None = None
    status: RequestStatus = RequestStatus.CREATED
    current_stage: str = "request_received"
    summary: str = ""


@dataclass(frozen=True, slots=True)
class RoutingSection:
    status: RoutingStatus = RoutingStatus.PENDING
    message_category: RouterMessageCategory | None = None
    selected_department: DepartmentType | None = None
    confidence: str | None = None
    needs_clarification: bool = False
    clarification_count: int = 0
    latest_question: str | None = None
    latest_answer: str | None = None
    request_type: str | None = None
    short_summary: str | None = None
    routing_reason: str | None = None
    unsupported_reason: str | None = None
    is_capability_gap: bool = False
    platform_answer: str | None = None


@dataclass(frozen=True, slots=True)
class PlanningSection:
    initial_plan: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    pending_steps: list[str] = field(default_factory=list)
    current_step: str | None = None
    plan_revision_count: int = 0


@dataclass(frozen=True, slots=True)
class ExecutionSection:
    status: ExecutionStatus = ExecutionStatus.PENDING
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    department_result: dict[str, Any] = field(default_factory=dict)
    department_data: dict[str, Any] = field(default_factory=dict)
    last_operation: str | None = None
    retry_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CollaborationSection:
    sender_department: DepartmentType | None = None
    receiver_department: DepartmentType | None = None
    action: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    is_active: bool = False
    depth: int = 0
    total_calls: int = 0


@dataclass(frozen=True, slots=True)
class ReviewSection:
    required: bool = False
    status: str = "not_required"
    feedback: str | None = None
    decision: str | None = None
    revision_count: int = 0


@dataclass(frozen=True, slots=True)
class HumanActionSection:
    required: bool = False
    action_type: str | None = None
    assigned_user_id: UUID | None = None
    decision_package: dict[str, Any] = field(default_factory=dict)
    status: str | None = None
    response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FailureSection:
    has_failure: bool = False
    failure_type: str | None = None
    safe_message: str | None = None
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class ResultSection:
    decision: str | None = None
    reason: str | None = None
    final_response: str | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class WorkflowState:
    """Complete workflow state organized into sections."""

    state_version: int = 1
    request: RequestSection = field(default_factory=lambda: RequestSection(
        request_id=UUID(int=0), company_id=UUID(int=0),
        requester_user_id=UUID(int=0), summary=""
    ))
    routing: RoutingSection = field(default_factory=RoutingSection)
    planning: PlanningSection = field(default_factory=PlanningSection)
    execution: ExecutionSection = field(default_factory=ExecutionSection)
    collaboration: CollaborationSection = field(default_factory=CollaborationSection)
    review: ReviewSection = field(default_factory=ReviewSection)
    human_action: HumanActionSection = field(default_factory=HumanActionSection)
    failure: FailureSection = field(default_factory=FailureSection)
    result: ResultSection = field(default_factory=ResultSection)

    # --- convenience ---

    def with_routing(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, routing=replace(self.routing, **kwargs))

    def with_execution(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, execution=replace(self.execution, **kwargs))

    def with_request(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, request=replace(self.request, **kwargs))

    def with_planning(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, planning=replace(self.planning, **kwargs))

    def with_collaboration(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, collaboration=replace(self.collaboration, **kwargs))

    def with_review(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, review=replace(self.review, **kwargs))

    def with_human_action(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, human_action=replace(self.human_action, **kwargs))

    def with_failure(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, failure=replace(self.failure, **kwargs))

    def with_result(self, **kwargs: Any) -> "WorkflowState":
        return replace(self, result=replace(self.result, **kwargs))

    # --- serialization ---

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict safe for JSONB storage."""
        return {
            "state_version": self.state_version,
            "request": self._section_to_dict(self.request),
            "routing": self._section_to_dict(self.routing),
            "planning": self._section_to_dict(self.planning),
            "execution": self._section_to_dict(self.execution),
            "collaboration": self._section_to_dict(self.collaboration),
            "review": self._section_to_dict(self.review),
            "human_action": self._section_to_dict(self.human_action),
            "failure": self._section_to_dict(self.failure),
            "result": self._section_to_dict(self.result),
        }

    @staticmethod
    def _section_to_dict(section: Any) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in getattr(section, "__slots__", ()):
            v = getattr(section, k)
            if isinstance(v, UUID):
                d[k] = str(v)
            elif isinstance(v, datetime):
                d[k] = v.isoformat() if v else None
            elif isinstance(v, StrEnum):
                d[k] = v.value
            elif isinstance(v, DepartmentType):
                d[k] = v.value
            elif isinstance(v, RequestStatus):
                d[k] = v.value
            else:
                d[k] = v
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowState":
        """Reconstruct from a dict previously stored in JSONB."""
        return cls(
            state_version=data.get("state_version", 1),
            request=cls._load_request(data.get("request", {})),
            routing=cls._load_routing(data.get("routing", {})),
            planning=cls._load_planning(data.get("planning", {})),
            execution=cls._load_execution(data.get("execution", {})),
            collaboration=cls._load_collaboration(data.get("collaboration", {})),
            review=cls._load_review(data.get("review", {})),
            human_action=cls._load_human_action(data.get("human_action", {})),
            failure=cls._load_failure(data.get("failure", {})),
            result=cls._load_result(data.get("result", {})),
        )

    @staticmethod
    def _load_request(d: dict[str, Any]) -> RequestSection:
        return RequestSection(
            request_id=UUID(d.get("request_id", "00000000-0000-0000-0000-000000000000")),
            company_id=UUID(d.get("company_id", "00000000-0000-0000-0000-000000000000")),
            requester_user_id=UUID(d.get("requester_user_id", "00000000-0000-0000-0000-000000000000")),
            requester_employee_id=UUID(d["requester_employee_id"]) if d.get("requester_employee_id") else None,
            request_type=d.get("request_type", ""),
            owner_department_id=UUID(d["owner_department_id"]) if d.get("owner_department_id") else None,
            owner_department_type=DepartmentType(d["owner_department_type"]) if d.get("owner_department_type") else None,
            active_department_id=UUID(d["active_department_id"]) if d.get("active_department_id") else None,
            active_department_type=DepartmentType(d["active_department_type"]) if d.get("active_department_type") else None,
            status=RequestStatus(d.get("status", "created")),
            current_stage=d.get("current_stage", "request_received"),
            summary=d.get("summary", ""),
        )

    @staticmethod
    def _load_routing(d: dict[str, Any]) -> RoutingSection:
        return RoutingSection(
            status=RoutingStatus(d.get("status", "pending")),
            message_category=RouterMessageCategory(d["message_category"]) if d.get("message_category") else None,
            selected_department=DepartmentType(d["selected_department"]) if d.get("selected_department") else None,
            confidence=d.get("confidence"),
            needs_clarification=d.get("needs_clarification", False),
            clarification_count=d.get("clarification_count", 0),
            latest_question=d.get("latest_question"),
            latest_answer=d.get("latest_answer"),
            request_type=d.get("request_type"),
            short_summary=d.get("short_summary"),
            routing_reason=d.get("routing_reason"),
            unsupported_reason=d.get("unsupported_reason"),
            is_capability_gap=d.get("is_capability_gap", False),
            platform_answer=d.get("platform_answer"),
        )

    @staticmethod
    def _load_planning(d: dict[str, Any]) -> PlanningSection:
        return PlanningSection(
            initial_plan=list(d.get("initial_plan", [])),
            completed_steps=list(d.get("completed_steps", [])),
            pending_steps=list(d.get("pending_steps", [])),
            current_step=d.get("current_step"),
            plan_revision_count=d.get("plan_revision_count", 0),
        )

    @staticmethod
    def _load_execution(d: dict[str, Any]) -> ExecutionSection:
        return ExecutionSection(
            status=ExecutionStatus(d.get("status", "pending")),
            tool_results=list(d.get("tool_results", [])),
            department_result=dict(d.get("department_result", {})),
            department_data=dict(d.get("department_data", {})),
            last_operation=d.get("last_operation"),
            retry_counts=dict(d.get("retry_counts", {})),
        )

    @staticmethod
    def _load_collaboration(d: dict[str, Any]) -> CollaborationSection:
        return CollaborationSection(
            sender_department=DepartmentType(d["sender_department"]) if d.get("sender_department") else None,
            receiver_department=DepartmentType(d["receiver_department"]) if d.get("receiver_department") else None,
            action=d.get("action"),
            payload=dict(d.get("payload", {})),
            result=dict(d.get("result", {})),
            is_active=d.get("is_active", False),
            depth=d.get("depth", 0),
            total_calls=d.get("total_calls", 0),
        )

    @staticmethod
    def _load_review(d: dict[str, Any]) -> ReviewSection:
        return ReviewSection(
            required=d.get("required", False),
            status=d.get("status", "not_required"),
            feedback=d.get("feedback"),
            decision=d.get("decision"),
            revision_count=d.get("revision_count", 0),
        )

    @staticmethod
    def _load_human_action(d: dict[str, Any]) -> HumanActionSection:
        return HumanActionSection(
            required=d.get("required", False),
            action_type=d.get("action_type"),
            assigned_user_id=UUID(d["assigned_user_id"]) if d.get("assigned_user_id") else None,
            decision_package=dict(d.get("decision_package", {})),
            status=d.get("status"),
            response=dict(d.get("response", {})),
        )

    @staticmethod
    def _load_failure(d: dict[str, Any]) -> FailureSection:
        return FailureSection(
            has_failure=d.get("has_failure", False),
            failure_type=d.get("failure_type"),
            safe_message=d.get("safe_message"),
            terminal=d.get("terminal", False),
        )

    @staticmethod
    def _load_result(d: dict[str, Any]) -> ResultSection:
        return ResultSection(
            decision=d.get("decision"),
            reason=d.get("reason"),
            final_response=d.get("final_response"),
            completed_at=datetime.fromisoformat(d["completed_at"]) if d.get("completed_at") else None,
        )
