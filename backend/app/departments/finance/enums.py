from enum import StrEnum


class FinanceRequestCategory(StrEnum):
    FINANCE_INFORMATION = "finance_information"
    BUDGET_INQUIRY = "budget_inquiry"
    BUDGET_VALIDATION = "budget_validation"
    PURCHASE_VALIDATION = "purchase_validation"
    EXPENSE_POLICY = "expense_policy"
    BUDGET_RESERVATION = "budget_reservation"
    TRANSACTION_CONFIRMATION = "transaction_confirmation"
    IT_PURCHASE_VALIDATION = "it_purchase_validation"
    PROCUREMENT_PURCHASE_VALIDATION = "procurement_purchase_validation"
    HUMAN_APPROVAL_REQUIRED = "human_approval_required"
    UNSUPPORTED = "unsupported"


class FinanceDecision(StrEnum):
    ANSWER = "answer"
    VALIDATED = "validated"
    REJECTED = "rejected"
    APPROVAL_REQUIRED = "approval_required"
    RESERVED = "reserved"
    RELEASED = "released"
    TRANSACTION_RECORDED = "transaction_recorded"
    CLARIFY = "clarify"
    RETURN_TO_IT = "return_to_it"
    RETURN_TO_PROCUREMENT = "return_to_procurement"
    USE_TOOL = "use_tool"
    UNSUPPORTED = "unsupported"


class BudgetType(StrEnum):
    COMPANY = "company"
    DEPARTMENT = "department"
    PROJECT = "project"
    OPERATIONAL = "operational"
    CAPITAL = "capital"


class BudgetStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class FinanceApprovalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReservationStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    RESERVED = "reserved"
    RELEASED = "released"
    FAILED = "failed"


class FinancialTransactionType(StrEnum):
    RESERVATION = "reservation"
    COMMITMENT = "commitment"
    EXPENSE = "expense"
    RELEASE = "release"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"


class FinancialTransactionStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    REVERSED = "reversed"


class FinanceModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
