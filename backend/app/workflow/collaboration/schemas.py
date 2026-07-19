from datetime import date
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.workflow.collaboration.enums import CollaborationRuntimeStatus


class StrictCollaborationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnoseExternalTechnicalIssueRequest(StrictCollaborationSchema):
    issue_summary: str = Field(min_length=1, max_length=2_000)
    product_or_service: str | None = Field(default=None, max_length=255)
    symptoms: list[str] = Field(default_factory=list, max_length=25)
    safe_error_details: list[str] = Field(default_factory=list, max_length=25)
    requester_impact: str | None = Field(default=None, max_length=1_000)
    completed_troubleshooting: list[str] = Field(default_factory=list, max_length=25)
    urgency: str | None = Field(default=None, max_length=50)
    source_references: list[dict[str, Any]] = Field(default_factory=list, max_length=25)


class DiagnoseExternalTechnicalIssueResult(StrictCollaborationSchema):
    diagnosis_status: str = Field(min_length=1, max_length=100)
    diagnosis_category: str | None = Field(default=None, max_length=100)
    additional_troubleshooting: list[str] = Field(default_factory=list, max_length=25)
    technician_action_required: bool = False
    internal_resolution_summary: str = Field(min_length=1, max_length=2_000)
    safe_customer_support_response: str = Field(min_length=1, max_length=2_000)
    confidence: Literal["low", "medium", "high"] = "medium"
    unresolved_reason: str | None = Field(default=None, max_length=1_000)


class ValidateITPurchaseBudgetRequest(StrictCollaborationSchema):
    asset_or_software: str = Field(min_length=1, max_length=255)
    quantity: int = Field(default=1, ge=1, le=100_000)
    estimated_cost: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    business_reason: str = Field(min_length=1, max_length=2_000)
    urgency: str | None = Field(default=None, max_length=50)
    inventory_context: dict[str, Any] = Field(default_factory=dict)
    employee_id: UUID | None = None
    department_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class FinanceValidationResult(StrictCollaborationSchema):
    finance_decision: str = Field(min_length=1, max_length=100)
    validated_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    budget_sufficient: bool | None = None
    approval_required: bool = False
    reservation_reference: str | None = Field(default=None, max_length=255)
    reason: str = Field(min_length=1, max_length=2_000)
    required_next_action: str | None = Field(default=None, max_length=100)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ValidateITPurchaseBudgetResult(FinanceValidationResult):
    pass


class FindITAssetSuppliersRequest(StrictCollaborationSchema):
    asset_or_software: str = Field(min_length=1, max_length=255)
    specification: dict[str, Any] = Field(default_factory=dict)
    quantity: int = Field(default=1, ge=1, le=100_000)
    maximum_budget: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(min_length=3, max_length=3)
    delivery_location: str | None = Field(default=None, max_length=500)
    required_by_date: date | None = None
    evaluation_criteria: dict[str, Decimal] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class FindITAssetSuppliersResult(StrictCollaborationSchema):
    eligible_candidate_count: int = Field(ge=0)
    shortlist: list[dict[str, Any]] = Field(default_factory=list, max_length=25)
    recommendation: dict[str, Any] | None = None
    estimated_total_costs: list[dict[str, Any]] = Field(default_factory=list, max_length=25)
    finance_revalidation_required: bool = False
    reason: str = Field(min_length=1, max_length=2_000)
    required_next_action: str | None = Field(default=None, max_length=100)


class ValidateProcurementPurchaseRequest(StrictCollaborationSchema):
    candidate_reference: str = Field(min_length=1, max_length=255)
    total_amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    delivery_amount: Decimal = Field(default=Decimal("0"), ge=0)
    requesting_department_id: UUID | None = None
    business_reason: str = Field(min_length=1, max_length=2_000)
    previous_finance_validation: dict[str, Any] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ValidateProcurementPurchaseResult(FinanceValidationResult):
    commitment_reference: str | None = Field(default=None, max_length=255)


class PrepareEmployeeOnboardingITRequest(StrictCollaborationSchema):
    employee_id: UUID
    role_title: str = Field(min_length=1, max_length=255)
    department_id: UUID | None = None
    manager_user_id: UUID | None = None
    start_date: date | None = None
    required_systems: list[str] = Field(default_factory=list, max_length=50)
    required_hardware: list[str] = Field(default_factory=list, max_length=50)
    urgency: str | None = Field(default=None, max_length=50)


class PrepareEmployeeOnboardingITResult(StrictCollaborationSchema):
    access_preparation: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    hardware_availability: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    missing_information: list[str] = Field(default_factory=list, max_length=25)
    approval_required: bool = False
    human_physical_action_required: bool = False
    readiness_status: str = Field(min_length=1, max_length=100)


class CollaborationCallState(StrictCollaborationSchema):
    collaboration_id: UUID
    status: CollaborationRuntimeStatus
    request_id: UUID
    sender_department: DepartmentType
    receiver_department: DepartmentType
    action: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any]
    expected_output: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] = Field(default_factory=dict)
    started_at: str
    completed_at: str | None = None
    attempt_count: int = Field(default=0, ge=0)
    depth: int = Field(ge=1)
    return_stage: str = Field(min_length=1, max_length=255)
    parent_collaboration_id: UUID | None = None
    idempotency_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_signature: str = Field(min_length=1, max_length=255)
    error_safe: str | None = Field(default=None, max_length=2_000)


class CollaborationHistoryEntry(StrictCollaborationSchema):
    collaboration_id: UUID
    parent_collaboration_id: UUID | None = None
    sender_department: DepartmentType
    receiver_department: DepartmentType
    action: str
    status: CollaborationRuntimeStatus
    idempotency_key: str
    route_signature: str
    depth: int
    attempt_count: int
    started_at: str
    completed_at: str | None = None
    safe_summary: str = Field(min_length=1, max_length=1_000)
    safe_result: dict[str, Any] = Field(default_factory=dict)


class CollaborationReceiverOutcome(StrictCollaborationSchema):
    result: dict[str, Any] | None = None
    reason: str = Field(min_length=1, max_length=2_000)
    nested_request: DepartmentCollaborationRequest | None = None
    human_action: dict[str, Any] | None = None
    continuation_data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def exactly_one_outcome(self) -> "CollaborationReceiverOutcome":
        values = (self.result is not None, self.nested_request is not None, self.human_action is not None)
        if sum(values) != 1:
            raise ValueError("receiver outcome must contain exactly one next step")
        return self
