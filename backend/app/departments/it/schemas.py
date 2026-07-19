from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import ActorType, DepartmentType
from app.core.json_validation import validate_safe_json
from app.departments.contracts import (
    DepartmentCollaborationRequest, DepartmentCollaborationResult, DepartmentConfidence,
    DepartmentHumanActionRequest, DepartmentNextAction, DepartmentToolRequest,
)
from app.departments.it.enums import (
    AccessType, HardwareAssignmentStatus, ImpactLevel, IncidentSource, ITDecision,
    ITRequestCategory, PolicyDecision, ProvisioningStatus,
)
from app.rag.enums import KnowledgeDocumentType


class ITSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    version: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    effective_date: str | None = None


class ITDiagnosticStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,99}$")
    instruction: str = Field(min_length=1, max_length=1000)
    result: str | None = Field(default=None, max_length=1000)
    completed: bool = False


class ITAccessState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: UUID | None = None
    access_type: AccessType | None = None
    target_system: str | None = Field(default=None, max_length=255)
    requested_role: str | None = Field(default=None, max_length=255)
    business_reason: str | None = Field(default=None, max_length=2000)
    policy_decision: PolicyDecision = PolicyDecision.PENDING
    approval_required: bool = False
    provisioning_status: ProvisioningStatus = ProvisioningStatus.PENDING


class ITHardwareState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: UUID | None = None
    asset_type: str | None = Field(default=None, max_length=100)
    requested_specification: str | None = Field(default=None, max_length=2000)
    business_reason: str | None = Field(default=None, max_length=2000)
    inventory_checked: bool = False
    available_asset_id: UUID | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    budget_validation_required: bool = False
    procurement_required: bool = False
    assignment_status: HardwareAssignmentStatus = HardwareAssignmentStatus.PENDING


class ITIncidentState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    affected_employee_id: UUID | None = None
    source: IncidentSource = IncidentSource.EMPLOYEE
    symptoms: list[str] = Field(default_factory=list, max_length=30)
    error_messages: list[str] = Field(default_factory=list, max_length=20)
    impact: ImpactLevel = ImpactLevel.MEDIUM
    urgency: ImpactLevel = ImpactLevel.MEDIUM
    diagnostic_steps: list[ITDiagnosticStep] = Field(default_factory=list, max_length=30)
    resolution_summary: str | None = Field(default=None, max_length=5000)
    requires_human_technician: bool = False

    @field_validator("diagnostic_steps")
    @classmethod
    def unique_steps(cls, value: list[ITDiagnosticStep]) -> list[ITDiagnosticStep]:
        if len({step.step_id for step in value}) != len(value):
            raise ValueError("diagnostic steps must be unique")
        return value


class ITStateUpdates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    access: ITAccessState | None = None
    hardware: ITHardwareState | None = None
    incident: ITIncidentState | None = None


class ITDepartmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: ITRequestCategory
    decision: ITDecision
    reason: str = Field(min_length=1, max_length=2000)
    user_message: str = Field(min_length=1, max_length=5000)
    confidence: DepartmentConfidence
    sources_used: list[ITSourceReference] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    needs_user_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    request_approved_by_policy: bool | None = None
    requires_tool: bool = False
    tool_request: DepartmentToolRequest | None = None
    requires_finance_collaboration: bool = False
    finance_collaboration_request: DepartmentCollaborationRequest | None = None
    requires_procurement_collaboration: bool = False
    procurement_collaboration_request: DepartmentCollaborationRequest | None = None
    requires_human_action: bool = False
    human_action_request: DepartmentHumanActionRequest | None = None
    incident_resolved: bool = False
    next_action: DepartmentNextAction
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2000)
    state_updates: ITStateUpdates = Field(default_factory=ITStateUpdates)
    evidence_conflict: bool = False
    risk_indicators: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("clarification_question")
    @classmethod
    def one_question(cls, value: str | None) -> str | None:
        if value is not None and ("\n" in value or value.count("?") != 1):
            raise ValueError("clarification must be one concise question")
        return value

    @model_validator(mode="after")
    def validate_actions(self) -> "ITDepartmentResult":
        pairs = (
            (self.requires_tool, self.tool_request, "tool"),
            (self.requires_finance_collaboration, self.finance_collaboration_request, "finance"),
            (self.requires_procurement_collaboration, self.procurement_collaboration_request, "procurement"),
            (self.requires_human_action, self.human_action_request, "human action"),
        )
        for required, payload, label in pairs:
            if required != (payload is not None):
                raise ValueError(f"{label} fields are inconsistent")
        if self.needs_user_clarification != (self.clarification_question is not None):
            raise ValueError("clarification fields are inconsistent")
        primary_count = sum((self.needs_user_clarification, self.requires_tool,
            self.requires_finance_collaboration, self.requires_procurement_collaboration,
            self.requires_human_action))
        if primary_count > 1:
            raise ValueError("only one primary next action is allowed")
        expected = DepartmentNextAction.COMPLETE_REQUEST
        if self.needs_user_clarification:
            expected = DepartmentNextAction.WAIT_FOR_USER_INPUT
        elif self.requires_tool:
            expected = DepartmentNextAction.EXECUTE_TOOL
        elif self.requires_finance_collaboration or self.requires_procurement_collaboration:
            expected = DepartmentNextAction.COLLABORATE
        elif self.requires_human_action:
            expected = DepartmentNextAction.REQUEST_HUMAN_ACTION
        elif self.decision == ITDecision.UNSUPPORTED:
            expected = DepartmentNextAction.FAIL_REQUEST
        if self.next_action != expected:
            raise ValueError("next action contradicts the IT decision")
        if self.incident_resolved and self.requires_human_action:
            raise ValueError("a resolved incident cannot require technician action")
        collaboration = self.finance_collaboration_request or self.procurement_collaboration_request
        if collaboration is not None:
            expected_receiver = DepartmentType.FINANCE if self.requires_finance_collaboration else DepartmentType.PROCUREMENT
            expected_action = "validate_it_purchase_budget" if self.requires_finance_collaboration else "find_it_asset_suppliers"
            if collaboration.sender_department != DepartmentType.IT or collaboration.receiver_department != expected_receiver or collaboration.action != expected_action:
                raise ValueError("IT collaboration is outside the approved boundary")
        if self.requires_tool and self.tool_request.operation not in {
            "check_asset_inventory", "check_software_availability"
        }:
            raise ValueError("IT tool is not allowlisted")
        if self.category in {ITRequestCategory.IT_INFORMATION, ITRequestCategory.SOFTWARE_ACCESS,
            ITRequestCategory.PASSWORD_RESET, ITRequestCategory.ACCOUNT_UNLOCK,
            ITRequestCategory.ACCOUNT_PROVISIONING, ITRequestCategory.MFA_ACCESS} and self.request_approved_by_policy is not None and not self.sources_used:
            raise ValueError("policy decisions require authorized evidence")
        if self.category == ITRequestCategory.IT_INFORMATION and not self.sources_used:
            raise ValueError("IT informational answers require authorized evidence")
        if self.state_updates.access and self.state_updates.access.provisioning_status == ProvisioningStatus.COMPLETED:
            raise ValueError("IT may prepare but cannot claim access provisioning completed")
        if self.state_updates.hardware and self.state_updates.hardware.assignment_status == HardwareAssignmentStatus.COMPLETED:
            raise ValueError("IT may prepare but cannot claim physical assignment completed")
        return self


class ITExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    requester_department_id: UUID | None = None
    requester_actor_type: ActorType
    requester_is_manager: bool = False
    request_type: str
    original_summary: str
    latest_user_input: str | None = None
    current_stage: str
    completed_it_steps: list[str] = Field(default_factory=list)
    employee_data: dict[str, Any] = Field(default_factory=dict)
    existing_access: list[dict[str, Any]] = Field(default_factory=list)
    assigned_assets: list[dict[str, Any]] = Field(default_factory=list)
    inventory_results: list[dict[str, Any]] = Field(default_factory=list)
    software_results: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_input: DepartmentCollaborationRequest | None = None
    collaboration_result: DepartmentCollaborationResult | None = None
    review_feedback: dict[str, Any] = Field(default_factory=dict)
    human_response: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    previous_it_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("employee_data", "review_feedback", "human_response", "previous_it_state")
    @classmethod
    def safe_objects(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(value, path="it_context")
