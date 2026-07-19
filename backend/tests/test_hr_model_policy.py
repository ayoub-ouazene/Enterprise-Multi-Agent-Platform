from uuid import uuid4

from app.departments.hr.enums import HRModelRole
from app.departments.hr.model_policy import initial_model_role
from app.departments.hr.schemas import HRExecutionInput


def context(**updates) -> HRExecutionInput:
    values = dict(request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", requester_is_manager=False,
        owner_department_type="hr", active_department_type="hr", request_type="hr_information",
        original_summary="What is the leave policy?", current_stage="hr_analysis")
    values.update(updates)
    return HRExecutionInput(**values)


def test_fast_model_for_normal_hr_request() -> None:
    assert initial_model_role(context()) == HRModelRole.FAST


def test_reasoning_model_for_staffing_conflict() -> None:
    assert initial_model_role(context(staffing_result={"conflict": True})) == HRModelRole.REASONING
