from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
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
from app.departments.procurement.enums import (
    AvailabilityStatus,
    CandidateSourceType,
    ComplianceStatus,
    FinanceValidationStatus,
    ProcurementDecision,
    ProcurementRequestCategory,
    SelectionStatus,
    ShortlistStatus,
)
from app.departments.procurement.scoring import normalize_currency
from app.rag.enums import KnowledgeDocumentType


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProcurementSourceReference(StrictModel):
    document_id: UUID
    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    version: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    effective_date: str | None = None


class ProcurementCandidateSummary(StrictModel):
    candidate_id: UUID
    supplier_name: str = Field(min_length=1, max_length=255)
    total_cost: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str
    delivery_days: int | None = Field(default=None, ge=0)
    compliance_status: ComplianceStatus
    overall_score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)
    rank: int = Field(gt=0)
    recommendation_reason: str = Field(min_length=1, max_length=2000)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return normalize_currency(value)


class ProcurementStateUpdates(StrictModel):
    requesting_department_id: UUID | None = None
    item_or_service: str | None = Field(default=None, max_length=500)
    quantity: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=3
    )
    minimum_specifications: dict[str, Any] = Field(default_factory=dict)
    required_certifications: list[str] = Field(default_factory=list, max_length=100)
    delivery_location: str | None = Field(default=None, max_length=500)
    required_by_date: date | None = None
    estimated_budget: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )
    approved_budget: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )
    currency: str | None = None
    evaluation_criteria: dict[str, Any] = Field(default_factory=dict)
    finance_validation_status: FinanceValidationStatus = (
        FinanceValidationStatus.NOT_REQUIRED
    )
    shortlist_status: ShortlistStatus = ShortlistStatus.PENDING
    selection_status: SelectionStatus = SelectionStatus.NOT_REQUIRED
    selected_candidate_id: UUID | None = None

    @field_validator("minimum_specifications", "evaluation_criteria")
    @classmethod
    def safe_objects(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_safe_json(value, path="procurement_state")
        return value

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value) if value else None


class ProcurementDepartmentResult(StrictModel):
    category: ProcurementRequestCategory
    decision: ProcurementDecision
    reason: str = Field(min_length=1, max_length=2000)
    user_message: str = Field(min_length=1, max_length=5000)
    confidence: DepartmentConfidence
    sources_used: list[ProcurementSourceReference] = Field(
        default_factory=list, max_length=20
    )
    requirements_complete: bool
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    needs_user_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    candidate_count: int = Field(ge=0)
    eligible_candidate_count: int = Field(ge=0)
    shortlist: list[ProcurementCandidateSummary] = Field(default_factory=list, max_length=20)
    recommended_candidate_id: UUID | None = None
    recommendation_reason: str | None = Field(default=None, max_length=2000)
    requires_tool: bool = False
    tool_request: DepartmentToolRequest | None = None
    requires_finance_collaboration: bool = False
    finance_collaboration_request: DepartmentCollaborationRequest | None = None
    finance_result_received: bool = False
    requires_human_action: bool = False
    human_action_request: DepartmentHumanActionRequest | None = None
    purchase_execution_prohibited: Literal[True] = True
    next_action: DepartmentNextAction
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2000)
    state_updates: ProcurementStateUpdates = Field(default_factory=ProcurementStateUpdates)
    evidence_conflict: bool = False
    risk_indicators: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("clarification_question")
    @classmethod
    def one_question(cls, value: str | None) -> str | None:
        if value is not None and ("\n" in value or value.count("?") != 1):
            raise ValueError("clarification must be one concise question")
        return value

    @model_validator(mode="after")
    def consistent_result(self) -> "ProcurementDepartmentResult":
        pairs = (
            (self.needs_user_clarification, self.clarification_question, "clarification"),
            (self.requires_tool, self.tool_request, "tool"),
            (
                self.requires_finance_collaboration,
                self.finance_collaboration_request,
                "Finance collaboration",
            ),
            (self.requires_human_action, self.human_action_request, "human action"),
        )
        for required, payload, label in pairs:
            if required != (payload is not None):
                raise ValueError(f"{label} fields are inconsistent")
        if sum(
            (
                self.needs_user_clarification,
                self.requires_tool,
                self.requires_finance_collaboration,
                self.requires_human_action,
            )
        ) > 1:
            raise ValueError("only one primary Procurement action is allowed")
        if self.eligible_candidate_count > self.candidate_count:
            raise ValueError("eligible count cannot exceed candidate count")
        shortlist_ids = {item.candidate_id for item in self.shortlist}
        if len(shortlist_ids) != len(self.shortlist):
            raise ValueError("shortlist candidates must be unique")
        if self.recommended_candidate_id is not None:
            if self.recommended_candidate_id not in shortlist_ids:
                raise ValueError("recommended candidate must be in the eligible shortlist")
            if not self.recommendation_reason:
                raise ValueError("a recommendation requires a reason")
        if len(self.shortlist) > self.eligible_candidate_count:
            raise ValueError("shortlist cannot contain ineligible candidates")
        expected = DepartmentNextAction.COMPLETE_REQUEST
        if self.needs_user_clarification:
            expected = DepartmentNextAction.WAIT_FOR_USER_INPUT
        elif self.requires_tool:
            expected = DepartmentNextAction.EXECUTE_TOOL
        elif self.requires_finance_collaboration:
            expected = DepartmentNextAction.COLLABORATE
        elif self.requires_human_action:
            expected = DepartmentNextAction.REQUEST_HUMAN_ACTION
        elif self.decision == ProcurementDecision.UNSUPPORTED:
            expected = DepartmentNextAction.FAIL_REQUEST
        if self.next_action != expected:
            raise ValueError("next action contradicts Procurement fields")
        if self.requires_finance_collaboration:
            request = self.finance_collaboration_request
            if request is None or (
                request.sender_department != DepartmentType.PROCUREMENT
                or request.receiver_department != DepartmentType.FINANCE
                or request.action != "validate_procurement_purchase"
            ):
                raise ValueError("Finance collaboration contract is invalid")
        if self.requires_tool and self.tool_request is not None:
            if self.tool_request.operation not in {
                "list_supplier_candidates",
                "calculate_candidate_total_cost",
                "evaluate_supplier_eligibility",
                "score_supplier_candidates",
                "rank_supplier_candidates",
                "create_shortlist",
            }:
                raise ValueError("Procurement tool is not allowlisted")
        if self.state_updates.selected_candidate_id is not None:
            if (
                self.state_updates.selection_status != SelectionStatus.SELECTED
                or self.state_updates.selected_candidate_id not in shortlist_ids
                or self.state_updates.finance_validation_status
                != FinanceValidationStatus.APPROVED
            ):
                raise ValueError("supplier selection is not authorized")
        prohibited_claims = ("purchase completed", "payment sent", "contract signed")
        if any(claim in self.user_message.casefold() for claim in prohibited_claims):
            raise ValueError("Procurement cannot claim execution")
        return self


class ProcurementExecutionInput(StrictModel):
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    requester_department_id: UUID | None = None
    requester_actor_type: ActorType
    requester_is_manager: bool
    owner_department_type: DepartmentType
    active_department_type: DepartmentType
    originating_department_type: DepartmentType | None = None
    request_type: str
    original_summary: str
    latest_user_input: str | None = None
    current_stage: str
    purchase_requirement: dict[str, Any] = Field(default_factory=dict)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    finance_result: dict[str, Any] = Field(default_factory=dict)
    approval_state: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    collaboration_input: DepartmentCollaborationRequest | None = None
    collaboration_result: DepartmentCollaborationResult | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    previous_procurement_state: dict[str, Any] = Field(default_factory=dict)


class SupplierCandidateCreate(StrictModel):
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_reference: str | None = Field(default=None, max_length=255)
    contact_reference: str | None = Field(default=None, max_length=255)
    item_or_service: str = Field(min_length=1, max_length=500)
    quoted_unit_price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    currency: str
    delivery_cost: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    tax_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    delivery_days: int | None = Field(default=None, ge=0)
    warranty_months: int | None = Field(default=None, ge=0)
    meets_minimum_specification: bool = False
    compliance_status: ComplianceStatus = ComplianceStatus.PENDING
    availability_status: AvailabilityStatus = AvailabilityStatus.UNKNOWN
    quality_score: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=3)
    source_type: CandidateSourceType
    custom_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator(
        "quoted_unit_price",
        "quantity",
        "delivery_cost",
        "tax_amount",
        "quality_score",
        mode="before",
    )
    @classmethod
    def reject_floats(cls, value: Any) -> Any:
        if isinstance(value, float):
            raise ValueError("floating-point numeric values are prohibited")
        return value

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return normalize_currency(value)

    @field_validator("custom_data")
    @classmethod
    def safe_custom_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        validate_safe_json(value, path="supplier_candidate")
        return value


class SupplierCandidateUpdate(StrictModel):
    supplier_reference: str | None = Field(default=None, max_length=255)
    contact_reference: str | None = Field(default=None, max_length=255)
    quoted_unit_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    quantity: Decimal | None = Field(default=None, gt=0, decimal_places=3)
    currency: str | None = None
    delivery_cost: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    tax_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    delivery_days: int | None = Field(default=None, ge=0)
    warranty_months: int | None = Field(default=None, ge=0)
    meets_minimum_specification: bool | None = None
    compliance_status: ComplianceStatus | None = None
    availability_status: AvailabilityStatus | None = None
    quality_score: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=3)
    custom_data: dict[str, Any] | None = None

    @field_validator(
        "quoted_unit_price",
        "quantity",
        "delivery_cost",
        "tax_amount",
        "quality_score",
        mode="before",
    )
    @classmethod
    def reject_floats(cls, value: Any) -> Any:
        if isinstance(value, float):
            raise ValueError("floating-point numeric values are prohibited")
        return value

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value) if value else None

    @field_validator("custom_data")
    @classmethod
    def safe_custom_data(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is not None:
            validate_safe_json(value, path="supplier_candidate")
        return value


class ProcurementRequestResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    request_id: UUID
    category: ProcurementRequestCategory
    item_or_service: str
    quantity: Decimal
    minimum_specifications: dict[str, Any]
    required_certifications: list[Any]
    delivery_location: str | None
    required_by_date: date | None
    estimated_budget: Decimal | None
    approved_budget: Decimal | None
    currency: str
    evaluation_criteria: dict[str, Any]
    finance_validation_status: FinanceValidationStatus
    shortlist_status: ShortlistStatus
    selected_candidate_id: UUID | None
    selection_status: SelectionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class SupplierCandidateResponse(StrictModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: UUID
    request_id: UUID
    supplier_name: str
    supplier_reference: str | None
    item_or_service: str
    quoted_unit_price: Decimal
    quantity: Decimal
    currency: str
    delivery_cost: Decimal
    tax_amount: Decimal | None
    total_cost: Decimal
    delivery_days: int | None
    warranty_months: int | None
    meets_minimum_specification: bool
    compliance_status: ComplianceStatus
    availability_status: AvailabilityStatus
    quality_score: Decimal | None
    price_score: Decimal | None
    delivery_score: Decimal | None
    compliance_score: Decimal | None
    overall_score: Decimal | None
    rank: int | None
    evaluation_reason: str | None
    is_shortlisted: bool
    is_selected: bool
    source_type: CandidateSourceType
    created_at: datetime
    updated_at: datetime
