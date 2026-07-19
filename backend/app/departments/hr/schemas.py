from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import ActorType, DepartmentType
from app.core.json_validation import validate_safe_json
from app.departments.contracts import (
    DepartmentCollaborationRequest,
    DepartmentCollaborationResult,
    DepartmentConfidence,
    DepartmentHumanActionRequest,
    DepartmentNextAction,
    DepartmentToolRequest,
)
from app.departments.hr.enums import (
    ApprovalStatus, BalanceStatus, EligibilityStatus, HRDecision,
    HRRequestCategory, JobDescriptionStatus, LeaveDecision, LeaveType,
    OnboardingStatus, StaffingStatus,
)
from app.rag.enums import KnowledgeDocumentType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HRSourceReference(StrictModel):
    document_id: UUID
    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    version: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    effective_date: str | None = None


class JobDescriptionDraft(StrictModel):
    title: str = Field(min_length=1, max_length=255)
    department_id: UUID
    employment_type: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=5000)
    responsibilities: list[str] = Field(min_length=1, max_length=50)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    preferred_skills: list[str] = Field(default_factory=list, max_length=50)
    experience_level: str = Field(min_length=1, max_length=100)
    education_requirements: list[str] = Field(default_factory=list, max_length=30)
    reporting_to: str | None = Field(default=None, max_length=255)
    work_location: str | None = Field(default=None, max_length=255)
    status: JobDescriptionStatus = JobDescriptionStatus.DRAFT

    @model_validator(mode="after")
    def draft_only(self) -> "JobDescriptionDraft":
        if self.status != JobDescriptionStatus.DRAFT:
            raise ValueError("HR can create only job-description drafts")
        if set(map(str.casefold, self.required_skills)).intersection(map(str.casefold, self.preferred_skills)):
            raise ValueError("required and preferred skills must be distinct")
        return self


class HRStateUpdates(StrictModel):
    employee_id: UUID | None = None
    leave_type: LeaveType | None = None
    start_date: date | None = None
    end_date: date | None = None
    requested_days: Decimal | None = Field(default=None, gt=0, max_digits=7, decimal_places=2)
    leave_reason: str | None = Field(default=None, max_length=2000)
    eligibility_status: EligibilityStatus = EligibilityStatus.PENDING
    balance_status: BalanceStatus = BalanceStatus.PENDING
    staffing_status: StaffingStatus = StaffingStatus.PENDING
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    leave_decision: LeaveDecision = LeaveDecision.PENDING
    reserved_days: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=7, decimal_places=2)
    onboarding_status: OnboardingStatus | None = None
    onboarding_start_date: date | None = None
    onboarding_department_id: UUID | None = None
    onboarding_manager_employee_id: UUID | None = None
    onboarding_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    completed_onboarding_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    onboarding_missing_data: list[str] = Field(default_factory=list, max_length=50)
    job_description: JobDescriptionDraft | None = None
    clarification_question: str | None = Field(default=None, max_length=300)

    @field_validator("onboarding_actions", "completed_onboarding_actions")
    @classmethod
    def safe_actions(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in value:
            validate_safe_json(item, path="hr_onboarding")
        return value


class HRDepartmentResult(StrictModel):
    category: HRRequestCategory
    decision: HRDecision
    reason: str = Field(min_length=1, max_length=2000)
    user_message: str = Field(min_length=1, max_length=5000)
    confidence: DepartmentConfidence
    sources_used: list[HRSourceReference] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    needs_user_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    leave_eligible: bool | None = None
    leave_balance_sufficient: bool | None = None
    minimum_staffing_satisfied: bool | None = None
    approval_required: bool = False
    approval_reason: str | None = Field(default=None, max_length=2000)
    requires_human_action: bool = False
    human_action_request: DepartmentHumanActionRequest | None = None
    onboarding_actions: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    benefits_answer: str | None = Field(default=None, max_length=5000)
    job_description: JobDescriptionDraft | None = None
    requires_tool: bool = False
    tool_request: DepartmentToolRequest | None = None
    requires_it_collaboration: bool = False
    it_collaboration_request: DepartmentCollaborationRequest | None = None
    next_action: DepartmentNextAction
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2000)
    state_updates: HRStateUpdates = Field(default_factory=HRStateUpdates)
    evidence_conflict: bool = False
    risk_indicators: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("clarification_question")
    @classmethod
    def one_question(cls, value: str | None) -> str | None:
        if value is not None and ("\n" in value or value.count("?") != 1):
            raise ValueError("clarification must contain one concise question")
        return value

    @model_validator(mode="after")
    def consistent(self) -> "HRDepartmentResult":
        if self.needs_user_clarification != (self.clarification_question is not None):
            raise ValueError("clarification fields are inconsistent")
        if self.requires_tool != (self.tool_request is not None):
            raise ValueError("tool fields are inconsistent")
        if self.requires_human_action != (self.human_action_request is not None):
            raise ValueError("human-action fields are inconsistent")
        if self.requires_it_collaboration != (self.it_collaboration_request is not None):
            raise ValueError("IT collaboration fields are inconsistent")
        if self.approval_required and self.next_action == DepartmentNextAction.COMPLETE_REQUEST and self.state_updates.approval_status not in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}:
            raise ValueError("approval-required work cannot complete before approval")
        if self.decision == HRDecision.APPROVED and (self.leave_eligible is False or self.leave_balance_sufficient is False or self.minimum_staffing_satisfied is False):
            raise ValueError("ineligible leave cannot be approved")
        if self.job_description is not None and self.category != HRRequestCategory.JOB_DESCRIPTION:
            raise ValueError("job description is allowed only for its category")
        if self.benefits_answer is not None and self.category != HRRequestCategory.BENEFITS_INFORMATION:
            raise ValueError("benefits answer is allowed only for its category")
        expected = {
            DepartmentNextAction.EXECUTE_TOOL: self.requires_tool,
            DepartmentNextAction.COLLABORATE: self.requires_it_collaboration,
            DepartmentNextAction.REQUEST_HUMAN_ACTION: self.requires_human_action,
            DepartmentNextAction.WAIT_FOR_USER_INPUT: self.needs_user_clarification,
        }
        if self.next_action in expected and not expected[self.next_action]:
            raise ValueError("next action lacks its required payload")
        return self


class HRExecutionInput(StrictModel):
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    requester_department_id: UUID | None = None
    requester_actor_type: ActorType
    requester_is_manager: bool
    owner_department_type: DepartmentType
    active_department_type: DepartmentType
    request_type: str
    original_summary: str
    latest_user_input: str | None = None
    current_stage: str
    employee_data: dict[str, Any] = Field(default_factory=dict)
    leave_balances: list[dict[str, Any]] = Field(default_factory=list)
    leave_request: dict[str, Any] = Field(default_factory=dict)
    staffing_result: dict[str, Any] = Field(default_factory=dict)
    benefits_eligibility: dict[str, Any] = Field(default_factory=dict)
    onboarding_state: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_input: DepartmentCollaborationRequest | None = None
    collaboration_result: DepartmentCollaborationResult | None = None
    human_response: dict[str, Any] = Field(default_factory=dict)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    previous_hr_state: dict[str, Any] = Field(default_factory=dict)


class LeaveBalanceResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    employee_id: UUID
    leave_type: LeaveType
    year: int
    allocated_days: Decimal
    used_days: Decimal
    reserved_days: Decimal
    remaining_days: Decimal
    created_at: datetime
    updated_at: datetime


class LeaveRequestResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    request_id: UUID
    employee_id: UUID
    leave_type: LeaveType
    start_date: date
    end_date: date
    requested_days: Decimal
    eligibility_status: EligibilityStatus
    balance_status: BalanceStatus
    staffing_status: StaffingStatus
    approval_required: bool
    approval_status: ApprovalStatus
    decision: LeaveDecision
    decision_reason: str | None
    reserved_days: Decimal
    created_at: datetime
    updated_at: datetime
    decided_at: datetime | None
    cancelled_at: datetime | None


class OnboardingRequestResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    request_id: UUID
    employee_id: UUID
    start_date: date
    department_id: UUID
    manager_employee_id: UUID | None
    onboarding_status: OnboardingStatus
    required_actions: list[Any]
    completed_actions: list[Any]
    missing_data: list[Any]
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class JobDescriptionResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    request_id: UUID | None
    title: str
    department_id: UUID
    employment_type: str
    summary: str
    responsibilities: list[Any]
    required_skills: list[Any]
    preferred_skills: list[Any]
    experience_level: str
    education_requirements: list[Any]
    reporting_to: str | None
    work_location: str | None
    status: JobDescriptionStatus
    created_at: datetime
    updated_at: datetime
