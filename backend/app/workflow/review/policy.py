"""Deterministic review-trigger policy per department.

Review is mandatory when backend policy detects high-impact signals.
Departments may suggest review, but this policy has final authority.
"""

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionResult, DepartmentNextAction
from app.workflow.review.schemas import ReviewerDecision


# Thresholds and keyword sets for deterministic policy triggers
_HUMAN_ACTION_HIGH_IMPACT_KEYWORDS = frozenset({
    "urgent", "critical", "security", "breach", "fraud",
    "data_loss", "physical_harm", "legal", "compliance_violation",
})

_SECURITY_GUIDANCE_KEYWORDS = frozenset({
    "password", "reset", "account", "credential", "mfa", "2fa",
    "security_question", "disable", "lock", "unlock",
})

_DATA_LOSS_KEYWORDS = frozenset({
    "delete", "remove", "purge", "erase", "wipe", "reset",
})

_FINANCIAL_HARM_KEYWORDS = frozenset({
    "refund", "chargeback", "payment", "credit", "debit",
    "compensation", "reimburse",
})

_PRIVILEGED_ACCESS_KEYWORDS = frozenset({
    "admin", "root", "superuser", "privileged", "domain_admin",
    "all_access", "full_access",
})

_IDENTITY_VERIFICATION_KEYWORDS = frozenset({
    "identity", "verify", "verification", "kyc", "identification",
    "document", "passport", "id_card",
})

_RISKY_TECHNICAL_KEYWORDS = frozenset({
    "registry", "kernel", "boot", "firmware", "bios",
    "partition", "format", "reimage", "wipe",
})

_ADJUSTMENT_KEYWORDS = frozenset({
    "adjust", "adjustment", "correct", "correction", "reversal",
    "reverse", "amend", "amendment", "override", "exception",
})

_COMMITMENT_KEYWORDS = frozenset({
    "commit", "commitment", "obligate", "obligation", "contract",
    "sign", "bind", "binding",
})

_LEAVE_POLICY_EXCEPTION_KEYWORDS = frozenset({
    "exception", "override", "waive", "waiver", "special_case",
    "unusual", "extraordinary",
})

_STAFFING_CONFLICT_KEYWORDS = frozenset({
    "understaffed", "minimum_staffing", "coverage_gap", "conflict",
    "overlap", "simultaneous",
})

_SUPPLIER_CLOSE_SCORE = 10.0  # percentage points
_PROCUREMENT_COMPLIANCE_RISK = frozenset({
    "non_compliant", "uncertain_compliance", "missing_certification",
    "expired_license",
})


def _any_keyword_present(text: str, keywords: frozenset[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _collaboration_context_has_finance_conflict(
    department_result: dict,
) -> bool:
    ctx = department_result.get("state_updates", {}).get("execution", {}).get("department_data", {})
    finance_state = ctx.get("finance_validation_state") or ctx.get("finqnce_result")
    if finance_state and isinstance(finance_state, dict):
        decision = finance_state.get("budget_validated") or finance_state.get("approved")
        if decision is False:
            return True
    return False


def _contains_high_impact_escalation(department_result: dict) -> bool:
    human_req = department_result.get("human_action_request") or {}
    if not human_req:
        return False
    summary = str(human_req.get("request_summary", ""))
    reason = str(human_req.get("reason", ""))
    text = summary + " " + reason
    return _any_keyword_present(text, _HUMAN_ACTION_HIGH_IMPACT_KEYWORDS)


def should_trigger_review(result: DepartmentExecutionResult) -> tuple[bool, str]:
    """Return (should_review, reason) based on deterministic backend policy.

    This function overrides any department-level `requires_review` flag.
    If policy says review is required, the result is reviewed regardless.
    """
    dept = result.department_type
    decision = result.decision.lower()
    reason = result.reason.lower()
    user_message = result.user_message.lower()
    combined = f"{decision} {reason} {user_message}"
    stage = result.current_stage.lower()
    next_action = result.next_action
    human_action = result.human_action_request
    collab_req = result.collaboration_request

    # --- High-impact human action always reviewed ---
    if human_action is not None and next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
        if _contains_high_impact_escalation(result.model_dump(mode="json")):
            return True, "high_impact_human_escalation"

    # --- Customer Support ---
    if dept == DepartmentType.CUSTOMER_SUPPORT:
        if _any_keyword_present(combined, _SECURITY_GUIDANCE_KEYWORDS):
            return True, "customer_support_risky_security_guidance"
        if _any_keyword_present(combined, _DATA_LOSS_KEYWORDS):
            return True, "customer_support_possible_data_loss"
        if _any_keyword_present(combined, _FINANCIAL_HARM_KEYWORDS):
            return True, "customer_support_possible_financial_harm"
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            return True, "customer_support_human_escalation"
        if result.requires_collaboration and collab_req and collab_req.action == "diagnose_external_technical_issue":
            # Low-risk collaboration (diagnosis) does not trigger review by default
            pass
        return False, "customer_support_low_risk_informational"

    # --- IT ---
    if dept == DepartmentType.IT:
        if _any_keyword_present(combined, _PRIVILEGED_ACCESS_KEYWORDS):
            return True, "it_privileged_access"
        if _any_keyword_present(combined, _IDENTITY_VERIFICATION_KEYWORDS):
            return True, "it_identity_verification"
        if _any_keyword_present(combined, _RISKY_TECHNICAL_KEYWORDS):
            return True, "it_risky_technical_instructions"
        # Expensive hardware: check if purchase path implied
        if "purchase" in combined or "buy" in combined or "order" in combined:
            tool_results = result.state_updates.execution.department_data if result.state_updates.execution else None
            if tool_results and isinstance(tool_results, dict):
                estimated_cost = tool_results.get("estimated_cost")
                if estimated_cost and float(str(estimated_cost)) > 500:
                    return True, "it_expensive_hardware_decision"
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            return True, "it_sensitive_technician_action"
        return False, "it_low_risk_informational"

    # --- Finance ---
    if dept == DepartmentType.FINANCE:
        dept_data = result.state_updates.execution.department_data if result.state_updates.execution else None
        if dept_data and isinstance(dept_data, dict):
            req_amount = dept_data.get("requested_amount")
            threshold = dept_data.get("approval_threshold")
            if req_amount and threshold and float(str(req_amount)) > float(str(threshold)):
                return True, "finance_spending_above_threshold"
        if _any_keyword_present(combined, _COMMITMENT_KEYWORDS):
            return True, "finance_commitment"
        if next_action == DepartmentNextAction.EXECUTE_TOOL:
            tool_req = result.tool_request
            if tool_req and tool_req.operation in {"record_financial_transaction", "commit_budget"}:
                return True, "finance_confirmed_transaction_preparation"
        if _any_keyword_present(combined, _ADJUSTMENT_KEYWORDS):
            return True, "finance_adjustment_or_reversal"
        if dept_data and isinstance(dept_data, dict):
            if dept_data.get("exception") or dept_data.get("override"):
                return True, "finance_exception"
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            return True, "finance_human_spending_approval_package"
        # Check for conflicting policy signal
        if "conflict" in reason or "contradict" in reason:
            return True, "finance_conflicting_financial_policy"
        return False, "finance_low_risk_informational"

    # --- Procurement ---
    if dept == DepartmentType.PROCUREMENT:
        dept_data = result.state_updates.execution.department_data if result.state_updates.execution else None
        if dept_data and isinstance(dept_data, dict):
            candidates = dept_data.get("candidates") or dept_data.get("shortlist")
            if candidates and len(candidates) >= 2:
                # Close scores check
                try:
                    scores = [float(c.get("score", 0)) for c in candidates[:2]]
                    if len(scores) == 2 and abs(scores[0] - scores[1]) <= _SUPPLIER_CLOSE_SCORE:
                        return True, "procurement_close_scores"
                except (ValueError, TypeError):
                    pass
        if dept_data and isinstance(dept_data, dict):
            if dept_data.get("recommendation") or dept_data.get("selected_candidate"):
                return True, "procurement_supplier_recommendation"
        if _any_keyword_present(combined, _PROCUREMENT_COMPLIANCE_RISK):
            return True, "procurement_uncertain_compliance"
        if _collaboration_context_has_finance_conflict(result.model_dump(mode="json")):
            return True, "procurement_conflict_with_finance_validation"
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            return True, "procurement_human_supplier_selection_package"
        return False, "procurement_low_risk_informational"

    # --- HR ---
    if dept == DepartmentType.HR:
        if _any_keyword_present(combined, _LEAVE_POLICY_EXCEPTION_KEYWORDS):
            return True, "hr_leave_policy_exception"
        if _any_keyword_present(combined, _STAFFING_CONFLICT_KEYWORDS):
            return True, "hr_staffing_conflict"
        dept_data = result.state_updates.execution.department_data if result.state_updates.execution else None
        if dept_data and isinstance(dept_data, dict):
            if dept_data.get("unusual_entitlement") or dept_data.get("exception"):
                return True, "hr_unusual_entitlement_decision"
        if next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION:
            return True, "hr_high_impact_manager_action_package"
        if "onboarding" in combined and "exception" in combined:
            return True, "hr_sensitive_onboarding_exception"
        return False, "hr_low_risk_informational"

    # Default: do not review unknown departments
    return False, "low_risk_or_unsupported_department"
