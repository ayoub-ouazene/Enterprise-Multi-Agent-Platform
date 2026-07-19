from app.departments.procurement.enums import ProcurementModelRole
from app.departments.procurement.schemas import (
    ProcurementDepartmentResult,
    ProcurementExecutionInput,
)


def initial_model_role(context: ProcurementExecutionInput) -> ProcurementModelRole:
    requirement = context.purchase_requirement
    complex_signals = (
        len(context.candidates) > 5,
        bool(requirement.get("policy_exception")),
        bool(requirement.get("multi_department")),
        bool(requirement.get("compliance_risk")),
        bool(requirement.get("conflicting_quotations")),
        bool(context.finance_result.get("approval_required")),
    )
    return (
        ProcurementModelRole.REASONING
        if any(complex_signals)
        else ProcurementModelRole.FAST
    )


def requires_reasoning_pass(
    result: ProcurementDepartmentResult,
    initial: ProcurementModelRole,
) -> bool:
    if initial == ProcurementModelRole.REASONING:
        return False
    return bool(
        result.evidence_conflict
        or result.risk_indicators
        or result.requires_human_action
        or result.decision.value == "human_selection_required"
    )
