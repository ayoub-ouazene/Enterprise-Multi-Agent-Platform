from app.departments.hr.enums import HRModelRole, HRRequestCategory
from app.departments.hr.schemas import HRDepartmentResult, HRExecutionInput


def initial_model_role(context: HRExecutionInput) -> HRModelRole:
    leave = context.leave_request
    complex_signals = (
        bool(leave.get("policy_exception")),
        bool(context.staffing_result.get("conflict")),
        bool(context.staffing_result.get("overlapping_absences")),
        bool(context.previous_hr_state.get("evidence_conflict")),
        bool(context.onboarding_state.get("multi_department")),
        context.request_type in {"policy_exception", "sensitive_hr_decision"},
    )
    return HRModelRole.REASONING if any(complex_signals) else HRModelRole.FAST


def requires_reasoning_pass(result: HRDepartmentResult, initial: HRModelRole) -> bool:
    if initial == HRModelRole.REASONING:
        return False
    return bool(
        result.evidence_conflict
        or result.risk_indicators
        or result.category in {
            HRRequestCategory.POLICY_EXCEPTION,
            HRRequestCategory.MANAGER_APPROVAL_REQUIRED,
        }
    )
