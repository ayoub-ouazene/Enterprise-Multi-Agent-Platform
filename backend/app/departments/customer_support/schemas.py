from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.departments.contracts import (
    DepartmentCollaborationResult,
    DepartmentCollaborationRequest,
    DepartmentConfidence,
    DepartmentHumanActionRequest,
    DepartmentNextAction,
)
from app.departments.customer_support.enums import CustomerSupportCategory, CustomerSupportDecision
from app.rag.enums import KnowledgeDocumentType


class SupportSourceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID
    title: str = Field(min_length=1, max_length=255)
    document_type: KnowledgeDocumentType
    version: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    effective_date: str | None = None


class TroubleshootingStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=1, max_length=1000)
    expected_result: str = Field(min_length=1, max_length=500)
    completed: bool = False


class CustomerSupportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: CustomerSupportCategory
    answer: str = Field(min_length=1, max_length=5000)
    decision: CustomerSupportDecision
    reason: str = Field(min_length=1, max_length=2000)
    confidence: DepartmentConfidence
    sources: list[SupportSourceReference] = Field(default_factory=list, max_length=20)
    missing_information: list[str] = Field(default_factory=list, max_length=20)
    needs_clarification: bool = False
    clarification_question: str | None = Field(default=None, max_length=300)
    issue_resolved: bool = False
    troubleshooting_steps: list[TroubleshootingStep] = Field(default_factory=list, max_length=20)
    requires_it_collaboration: bool = False
    it_collaboration_request: DepartmentCollaborationRequest | None = None
    requires_human_escalation: bool = False
    human_escalation_reason: str | None = Field(default=None, max_length=2000)
    human_action_request: DepartmentHumanActionRequest | None = None
    next_action: DepartmentNextAction
    safe_event_title: str = Field(min_length=1, max_length=255)
    safe_event_message: str = Field(min_length=1, max_length=2000)
    product_or_service: str | None = Field(default=None, max_length=255)
    symptoms: list[str] = Field(default_factory=list, max_length=30)
    error_messages: list[str] = Field(default_factory=list, max_length=20)
    customer_impact: str | None = Field(default=None, max_length=1000)
    evidence_conflict: bool = False
    risk_indicators: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_decision(self) -> "CustomerSupportResult":
        if self.needs_clarification != (self.clarification_question is not None):
            raise ValueError("clarification fields are inconsistent")
        if self.requires_it_collaboration != (self.it_collaboration_request is not None):
            raise ValueError("IT collaboration fields are inconsistent")
        if self.requires_human_escalation != (self.human_action_request is not None):
            raise ValueError("human escalation fields are inconsistent")
        expected = {
            CustomerSupportDecision.CLARIFY: DepartmentNextAction.WAIT_FOR_USER_INPUT,
            CustomerSupportDecision.PREPARE_IT_COLLABORATION: DepartmentNextAction.COLLABORATE,
            CustomerSupportDecision.PREPARE_HUMAN_ESCALATION: DepartmentNextAction.REQUEST_HUMAN_ACTION,
            CustomerSupportDecision.UNSUPPORTED: DepartmentNextAction.FAIL_REQUEST,
        }.get(self.decision, DepartmentNextAction.COMPLETE_REQUEST)
        if self.next_action != expected:
            raise ValueError("decision and next action are inconsistent")
        if self.category in {
            CustomerSupportCategory.FAQ,
            CustomerSupportCategory.PRODUCT_INFORMATION,
            CustomerSupportCategory.SERVICE_INFORMATION,
            CustomerSupportCategory.POLICY_EXPLANATION,
        } and not self.sources:
            raise ValueError("company-specific answers require authorized evidence")
        if self.requires_it_collaboration:
            request = self.it_collaboration_request
            if request is None or request.action != "diagnose_external_technical_issue":
                raise ValueError("only the approved IT diagnostic collaboration is allowed")
        return self


class CustomerSupportModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID
    message: str
    latest_user_input: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    issue_history: dict[str, Any] = Field(default_factory=dict)
    it_collaboration_result: DepartmentCollaborationResult | None = None
