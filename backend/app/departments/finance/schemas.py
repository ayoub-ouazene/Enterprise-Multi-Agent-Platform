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
from app.departments.finance.enums import (
    BudgetStatus,
    BudgetType,
    FinanceApprovalStatus,
    FinanceDecision,
    FinanceRequestCategory,
    FinancialTransactionStatus,
    FinancialTransactionType,
    ReservationStatus,
)
from app.rag.enums import KnowledgeDocumentType


Money = Decimal


def normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError("currency must be a three-letter code")
    return normalized


class FinanceSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    version: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    effective_date: str | None = None


class FinanceTransactionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_id: UUID
    transaction_type: FinancialTransactionType
    amount: Money = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str
    description: str = Field(min_length=1, max_length=1000)
    idempotency_reference: str = Field(
        min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
    )
    reversed_transaction_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str) -> str:
        return normalize_currency(value) or value

    @model_validator(mode="after")
    def reversal_link(self) -> "FinanceTransactionPayload":
        if (self.transaction_type == FinancialTransactionType.REVERSAL) != (
            self.reversed_transaction_id is not None
        ):
            raise ValueError("reversal transactions require exactly one original transaction")
        return self


class FinanceStateUpdates(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_id: UUID | None = None
    requesting_department_id: UUID | None = None
    business_reason: str | None = Field(default=None, max_length=2000)
    cost_center: str | None = Field(default=None, max_length=100)
    approval_status: FinanceApprovalStatus = FinanceApprovalStatus.NOT_REQUIRED
    reservation_status: ReservationStatus = ReservationStatus.NOT_REQUESTED
    safe_budget_reference: str | None = Field(default=None, max_length=255)


class FinanceDepartmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: FinanceRequestCategory
    decision: FinanceDecision
    reason: str = Field(min_length=1, max_length=2000)
    user_message: str = Field(min_length=1, max_length=5000)
    confidence: DepartmentConfidence
    sources_used: list[FinanceSourceReference] = Field(default_factory=list, max_length=20)
    requested_amount: Money | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    currency: str | None = None
    available_budget: Money | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )
    budget_sufficient: bool | None = None
    policy_compliant: bool | None = None
    approval_required: bool = False
    approval_reason: str | None = Field(default=None, max_length=2000)
    requires_user_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    requires_human_action: bool = False
    human_action_request: DepartmentHumanActionRequest | None = None
    requires_procurement_return: bool = False
    procurement_collaboration_result: DepartmentCollaborationResult | None = None
    requires_it_return: bool = False
    it_collaboration_result: DepartmentCollaborationResult | None = None
    requires_tool: bool = False
    tool_request: DepartmentToolRequest | None = None
    transaction_should_be_created: bool = False
    transaction_payload: FinanceTransactionPayload | None = None
    next_action: DepartmentNextAction
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2000)
    state_updates: FinanceStateUpdates = Field(default_factory=FinanceStateUpdates)
    evidence_conflict: bool = False
    risk_indicators: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @field_validator("clarification_question")
    @classmethod
    def one_question(cls, value: str | None) -> str | None:
        if value is not None and ("\n" in value or value.count("?") != 1):
            raise ValueError("clarification must be one concise question")
        return value

    @model_validator(mode="after")
    def validate_decision(self) -> "FinanceDepartmentResult":
        pairs = (
            (self.requires_user_clarification, self.clarification_question, "clarification"),
            (self.requires_human_action, self.human_action_request, "human action"),
            (self.requires_tool, self.tool_request, "tool"),
            (self.requires_it_return, self.it_collaboration_result, "IT result"),
            (
                self.requires_procurement_return,
                self.procurement_collaboration_result,
                "Procurement result",
            ),
            (
                self.transaction_should_be_created,
                self.transaction_payload,
                "transaction payload",
            ),
        )
        for required, payload, label in pairs:
            if required != (payload is not None):
                raise ValueError(f"{label} fields are inconsistent")
        if sum((self.requires_user_clarification, self.requires_human_action, self.requires_tool)) > 1:
            raise ValueError("only one primary Finance action is allowed")
        if self.requires_it_return and self.requires_procurement_return:
            raise ValueError("Finance can return to only one collaborating department")
        expected = DepartmentNextAction.COMPLETE_REQUEST
        if self.requires_user_clarification:
            expected = DepartmentNextAction.WAIT_FOR_USER_INPUT
        elif self.requires_human_action:
            expected = DepartmentNextAction.REQUEST_HUMAN_ACTION
        elif self.requires_tool:
            expected = DepartmentNextAction.EXECUTE_TOOL
        elif self.decision == FinanceDecision.UNSUPPORTED:
            expected = DepartmentNextAction.FAIL_REQUEST
        if self.next_action != expected:
            raise ValueError("next action contradicts the Finance decision")
        if self.budget_sufficient is False and self.decision in {
            FinanceDecision.VALIDATED,
            FinanceDecision.RESERVED,
            FinanceDecision.TRANSACTION_RECORDED,
        }:
            raise ValueError("an insufficient budget cannot be validated or mutated")
        if self.approval_required:
            if not self.approval_reason:
                raise ValueError("approval-required decisions need a reason")
            if self.next_action == DepartmentNextAction.COMPLETE_REQUEST and (
                self.state_updates.approval_status != FinanceApprovalStatus.APPROVED
            ):
                raise ValueError("approval-required work cannot complete before approval")
        if self.transaction_should_be_created:
            if not self.requires_tool or self.tool_request is None:
                raise ValueError("transactions must use a controlled Finance tool")
            if self.tool_request.operation != "record_financial_transaction":
                raise ValueError("transaction creation requires the transaction tool")
        if self.requires_tool and self.tool_request is not None and self.tool_request.operation not in {
            "get_budget_status",
            "validate_budget_availability",
            "reserve_budget",
            "release_budget_reservation",
            "record_financial_transaction",
        }:
            raise ValueError("Finance tool is not allowlisted")
        if (self.requested_amount is None) != (self.currency is None):
            raise ValueError("amount and currency must be provided together")
        if self.category in {
            FinanceRequestCategory.FINANCE_INFORMATION,
            FinanceRequestCategory.EXPENSE_POLICY,
        } and not self.sources_used:
            raise ValueError("Finance informational answers require authorized evidence")
        self._validate_collaboration_result()
        return self

    def _validate_collaboration_result(self) -> None:
        result = self.it_collaboration_result or self.procurement_collaboration_result
        if result is None:
            return
        receiver = DepartmentType.IT if self.requires_it_return else DepartmentType.PROCUREMENT
        expected_action = (
            "validate_it_purchase_budget"
            if receiver == DepartmentType.IT
            else "validate_procurement_purchase"
        )
        if (
            result.request_id is None
            or result.sender_department != DepartmentType.FINANCE
            or result.receiver_department != receiver
            or result.action != expected_action
        ):
            raise ValueError("Finance collaboration result is outside the approved boundary")


class FinanceExecutionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    company_id: UUID
    requester_user_id: UUID
    requester_employee_id: UUID | None = None
    requester_department_id: UUID | None = None
    requester_actor_type: ActorType
    requester_is_manager: bool = False
    owner_department_type: DepartmentType
    active_department_type: DepartmentType
    originating_department_type: DepartmentType | None = None
    request_type: str
    original_summary: str
    latest_user_input: str | None = None
    current_stage: str
    requested_amount: Money | None = Field(
        default=None, gt=0, max_digits=18, decimal_places=2
    )
    currency: str | None = None
    budget: dict[str, Any] = Field(default_factory=dict)
    cost_center: str | None = None
    relevant_transactions: list[dict[str, Any]] = Field(default_factory=list, max_length=25)
    business_justification: str | None = None
    urgency: str | None = None
    supplier_context: dict[str, Any] = Field(default_factory=dict)
    approval_state: dict[str, Any] = Field(default_factory=dict)
    collaboration_input: DepartmentCollaborationRequest | None = None
    collaboration_result: DepartmentCollaborationResult | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    previous_finance_state: dict[str, Any] = Field(default_factory=dict)

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, value: str | None) -> str | None:
        return normalize_currency(value)

    @field_validator("budget", "supplier_context", "approval_state", "previous_finance_state")
    @classmethod
    def safe_objects(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(value, path="finance_context")


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    department_id: UUID | None
    name: str
    budget_type: BudgetType
    currency: str
    period_start: date
    period_end: date
    allocated_amount: Money
    reserved_amount: Money
    committed_amount: Money
    spent_amount: Money
    available_amount: Money
    status: BudgetStatus
    approval_threshold: Money | None
    created_at: datetime
    updated_at: datetime


class FinancialTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    request_id: UUID | None
    budget_id: UUID
    transaction_type: FinancialTransactionType
    amount: Money
    currency: str
    status: FinancialTransactionStatus
    description: str
    reference: str
    confirmed_at: datetime | None
    reversed_transaction_id: UUID | None
    created_at: datetime
