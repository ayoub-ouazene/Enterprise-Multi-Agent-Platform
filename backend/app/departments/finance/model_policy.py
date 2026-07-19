from app.departments.contracts import DepartmentConfidence
from app.departments.finance.enums import FinanceModelRole
from app.departments.finance.schemas import FinanceDepartmentResult, FinanceExecutionInput


COMPLEX_REQUEST_TYPES = frozenset({
    "multi_budget_validation",
    "multi_cost_center_validation",
    "budget_exception",
    "high_impact_spending",
})


def initial_model_role(context: FinanceExecutionInput) -> FinanceModelRole:
    if context.request_type in COMPLEX_REQUEST_TYPES:
        return FinanceModelRole.REASONING
    collaboration = context.collaboration_input
    if collaboration is not None:
        payload = collaboration.payload
        if payload.get("policy_exception") is True or payload.get("multiple_budgets") is True:
            return FinanceModelRole.REASONING
    return FinanceModelRole.FAST


def requires_reasoning_pass(
    result: FinanceDepartmentResult,
    initial: FinanceModelRole,
) -> bool:
    if initial == FinanceModelRole.REASONING:
        return False
    return bool(
        result.evidence_conflict
        or result.risk_indicators
        or result.confidence == DepartmentConfidence.LOW
        or result.approval_required
        or result.category.value in {
            "it_purchase_validation",
            "procurement_purchase_validation",
            "human_approval_required",
        }
    )
