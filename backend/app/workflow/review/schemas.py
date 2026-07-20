"""Strict schemas for the centralized Reviewer Agent."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import DepartmentType
from app.departments.contracts import StrictContract


class ReviewerDecision(StrEnum):
    APPROVED = "approved"
    REVISION_REQUIRED = "revision_required"
    REJECTED = "rejected"
    HUMAN_ESCALATION_REQUIRED = "human_escalation_required"


class ReviewerSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GroundingStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    MISSING = "missing"
    CONFLICT = "conflict"
    UNCHECKED = "unchecked"


class ConsistencyStatus(StrEnum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    MISMATCH = "mismatch"
    UNCHECKED = "unchecked"


class AuthorizationStatus(StrEnum):
    VERIFIED = "verified"
    INSUFFICIENT = "insufficient"
    UNCHECKED = "unchecked"


class CompletenessStatus(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    UNCHECKED = "unchecked"


class SafetyStatus(StrEnum):
    SAFE = "safe"
    CAUTION = "caution"
    UNSAFE = "unsafe"
    UNCHECKED = "unchecked"


class RecommendedNextAction(StrEnum):
    APPROVE_AND_CONTINUE = "approve_and_continue"
    REVISE_ONCE = "revise_once"
    REJECT_AND_FAIL = "reject_and_fail"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class FeedbackCategory(StrEnum):
    POLICY = "policy"
    CALCULATION = "calculation"
    AUTHORIZATION = "authorization"
    COMPLETENESS = "completeness"
    SAFETY = "safety"
    PRIVACY = "privacy"
    WORKFLOW = "workflow"
    UNSUPPORTED_CLAIM = "unsupported_claim"


class DeterministicFact(StrictContract):
    """One authoritative fact checked against the department result."""

    fact_name: str = Field(min_length=1, max_length=255)
    authoritative_value: str | int | float | bool | None = None
    proposed_value: str | int | float | bool | None = None
    source_type: Literal[
        "database",
        "budget",
        "inventory",
        "leave_balance",
        "staffing",
        "supplier_candidate",
        "policy",
        "tool_result",
    ]
    source_reference: str = Field(min_length=1, max_length=500)
    match_status: Literal["match", "mismatch", "unchecked", "stale"] = "unchecked"


class FeedbackItem(StrictContract):
    """One structured feedback item from the Reviewer."""

    category: FeedbackCategory
    description: str = Field(min_length=1, max_length=2_000)
    required_change: str = Field(min_length=1, max_length=2_000)
    affected_field: str | None = Field(default=None, max_length=255)
    evidence_reference: str | None = Field(default=None, max_length=500)
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class ReviewPackage(StrictContract):
    """Everything the Reviewer needs to evaluate one department result."""

    request_id: UUID
    company_id: UUID
    owner_department: DepartmentType
    active_department: DepartmentType
    request_type: str = Field(min_length=1, max_length=100)
    request_summary: str = Field(min_length=1, max_length=2_000)
    department_result: dict[str, Any] = Field(default_factory=dict)
    proposed_decision: str = Field(min_length=1, max_length=500)
    proposed_reason: str = Field(min_length=1, max_length=2_000)
    proposed_user_message: str = Field(min_length=1, max_length=2_000)
    proposed_next_action: str = Field(min_length=1, max_length=100)
    policy_references: list[str] = Field(default_factory=list, max_length=100)
    evidence_references: list[str] = Field(default_factory=list, max_length=100)
    deterministic_facts: list[DeterministicFact] = Field(default_factory=list, max_length=50)
    safe_tool_result_summaries: list[str] = Field(default_factory=list, max_length=100)
    collaboration_context: dict[str, Any] | None = None
    human_action_package_summary: dict[str, Any] | None = None
    risk_flags: list[str] = Field(default_factory=list, max_length=50)
    review_reason: str = Field(min_length=1, max_length=500)
    review_attempt: int = Field(default=0, ge=0, le=2)
    revision_attempt: int = Field(default=0, ge=0, le=1)


class ReviewerResult(StrictContract):
    """Structured decision from the centralized Reviewer."""

    decision: ReviewerDecision
    reason: str = Field(min_length=1, max_length=2_000)
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    policy_grounding_status: GroundingStatus = GroundingStatus.UNCHECKED
    deterministic_consistency_status: ConsistencyStatus = ConsistencyStatus.UNCHECKED
    authorization_status: AuthorizationStatus = AuthorizationStatus.UNCHECKED
    completeness_status: CompletenessStatus = CompletenessStatus.UNCHECKED
    safety_status: SafetyStatus = SafetyStatus.UNCHECKED
    structured_feedback: list[FeedbackItem] = Field(default_factory=list, max_length=50)
    required_changes: list[str] = Field(default_factory=list, max_length=50)
    recommended_next_action: RecommendedNextAction = RecommendedNextAction.ESCALATE_TO_HUMAN
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2_000)
