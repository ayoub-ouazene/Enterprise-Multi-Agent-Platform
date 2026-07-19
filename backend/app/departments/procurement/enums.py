from enum import StrEnum


class ProcurementRequestCategory(StrEnum):
    PROCUREMENT_INFORMATION = "procurement_information"
    SUPPLIER_SEARCH = "supplier_search"
    SUPPLIER_EVALUATION = "supplier_evaluation"
    QUOTATION_COMPARISON = "quotation_comparison"
    PURCHASE_REQUIREMENT = "purchase_requirement"
    SHORTLIST_GENERATION = "shortlist_generation"
    FINANCE_VALIDATION = "finance_validation"
    HUMAN_SELECTION_REQUIRED = "human_selection_required"
    UNSUPPORTED = "unsupported"


class ProcurementDecision(StrEnum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    EVALUATED = "evaluated"
    SHORTLIST_READY = "shortlist_ready"
    FINANCE_VALIDATION_REQUIRED = "finance_validation_required"
    HUMAN_SELECTION_REQUIRED = "human_selection_required"
    RECOMMENDATION_READY = "recommendation_ready"
    SELECTION_RECORDED = "selection_recorded"
    NO_CANDIDATES = "no_candidates"
    NO_ELIGIBLE_CANDIDATES = "no_eligible_candidates"
    USE_TOOL = "use_tool"
    UNSUPPORTED = "unsupported"


class ProcurementModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"


class CandidateSourceType(StrEnum):
    COMPANY_CATALOG = "company_catalog"
    MANUAL_ENTRY = "manual_entry"
    PREVIOUS_SUPPLIER = "previous_supplier"
    DEPARTMENT_SUBMISSION = "department_submission"
    IMPORTED = "imported"
    OTHER = "other"


class ComplianceStatus(StrEnum):
    PENDING = "pending"
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    REQUIRES_REVIEW = "requires_review"


class AvailabilityStatus(StrEnum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"


class FinanceValidationStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPROVAL_REQUIRED = "approval_required"


class ShortlistStatus(StrEnum):
    PENDING = "pending"
    GENERATED = "generated"
    NO_ELIGIBLE_CANDIDATES = "no_eligible_candidates"


class SelectionStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    SELECTED = "selected"
    REJECTED = "rejected"
