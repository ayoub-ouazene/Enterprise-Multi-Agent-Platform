from uuid import uuid4

from app.core.enums import ActorType, DepartmentType
from app.departments.contracts import DepartmentConfidence, DepartmentNextAction
from app.departments.procurement.enums import (
    ProcurementDecision,
    ProcurementModelRole,
    ProcurementRequestCategory,
)
from app.departments.procurement.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.procurement.schemas import ProcurementDepartmentResult, ProcurementExecutionInput


def context(**requirement) -> ProcurementExecutionInput:
    return ProcurementExecutionInput(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type=ActorType.COMPANY, requester_is_manager=False,
        owner_department_type=DepartmentType.PROCUREMENT,
        active_department_type=DepartmentType.PROCUREMENT, request_type="procurement",
        original_summary="Compare suppliers", current_stage="processing",
        purchase_requirement=requirement,
    )


def result(**updates) -> ProcurementDepartmentResult:
    values = dict(
        category=ProcurementRequestCategory.PROCUREMENT_INFORMATION,
        decision=ProcurementDecision.ANSWER,
        reason="Policy evidence supports the answer.", user_message="Policy answer.",
        confidence=DepartmentConfidence.HIGH, requirements_complete=True,
        candidate_count=0, eligible_candidate_count=0,
        next_action=DepartmentNextAction.COMPLETE_REQUEST,
        safe_event_title="Procurement answered",
        safe_event_message="The policy question was answered.",
    )
    values.update(updates)
    return ProcurementDepartmentResult(**values)


def test_fast_model_is_used_for_simple_procurement_work() -> None:
    assert initial_model_role(context(item_or_service="laptop")) == ProcurementModelRole.FAST


def test_reasoning_model_is_used_for_complex_work() -> None:
    assert initial_model_role(context(policy_exception=True)) == ProcurementModelRole.REASONING


def test_risk_can_trigger_one_reasoning_pass() -> None:
    assert requires_reasoning_pass(result(risk_indicators=["compliance review"]), ProcurementModelRole.FAST)
    assert not requires_reasoning_pass(result(), ProcurementModelRole.REASONING)
