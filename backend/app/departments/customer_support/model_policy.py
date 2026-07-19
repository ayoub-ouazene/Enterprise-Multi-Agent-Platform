from app.departments.contracts import DepartmentConfidence
from app.departments.customer_support.enums import CustomerSupportCategory
from app.departments.customer_support.schemas import CustomerSupportResult


def requires_reasoning_pass(result: CustomerSupportResult) -> bool:
    """Deterministic escalation after a valid Fast-model result; at most one pass."""

    return bool(
        result.evidence_conflict
        or result.risk_indicators
        or result.confidence == DepartmentConfidence.LOW
        or result.requires_it_collaboration
        or result.requires_human_escalation
        or result.category == CustomerSupportCategory.TECHNICAL_ISSUE
        and len(result.troubleshooting_steps) > 2
    )
