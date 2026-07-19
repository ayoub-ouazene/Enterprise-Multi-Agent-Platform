from app.departments.contracts import DepartmentConfidence
from app.departments.it.enums import ITModelRole, ITRequestCategory
from app.departments.it.schemas import ITDepartmentResult, ITExecutionInput


COMPLEX_REQUEST_TYPES = frozenset({"complex_incident", "multi_system_access", "external_customer_incident"})


def initial_model_role(context: ITExecutionInput) -> ITModelRole:
    if context.request_type in COMPLEX_REQUEST_TYPES:
        return ITModelRole.REASONING
    collaboration = context.collaboration_input
    if collaboration is not None and collaboration.action == "diagnose_external_technical_issue":
        symptoms = collaboration.payload.get("symptoms", [])
        if len(symptoms) > 2 or collaboration.payload.get("evidence_conflict") is True:
            return ITModelRole.REASONING
    if collaboration is not None and collaboration.action == "prepare_employee_onboarding_it":
        if collaboration.payload.get("multi_department") or len(collaboration.payload.get("required_systems", [])) > 3:
            return ITModelRole.REASONING
    return ITModelRole.FAST


def requires_reasoning_pass(result: ITDepartmentResult, initial: ITModelRole) -> bool:
    if initial == ITModelRole.REASONING:
        return False
    return bool(result.evidence_conflict or result.risk_indicators
        or result.confidence == DepartmentConfidence.LOW
        or result.requires_finance_collaboration or result.requires_procurement_collaboration
        or result.category in {ITRequestCategory.EXTERNAL_CUSTOMER_INCIDENT,
            ITRequestCategory.HUMAN_TECHNICIAN_ESCALATION}
        or result.category == ITRequestCategory.EMPLOYEE_INCIDENT
        and result.state_updates.incident is not None
        and len(result.state_updates.incident.diagnostic_steps) > 2)
