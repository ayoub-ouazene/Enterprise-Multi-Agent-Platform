from uuid import uuid4
from app.departments.it.enums import ITModelRole
from app.departments.it.model_policy import initial_model_role, requires_reasoning_pass
from app.departments.it.schemas import ITExecutionInput
from tests.test_it_contracts import valid_it_result


def context(request_type="software_access"):
    return ITExecutionInput(request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_actor_type="employee", request_type=request_type, original_summary="Help",
        current_stage="it_analysis")


def test_simple_it_request_uses_fast_model() -> None:
    assert initial_model_role(context()) == ITModelRole.FAST
    assert requires_reasoning_pass(valid_it_result(), ITModelRole.FAST) is False


def test_complex_incident_uses_reasoning_without_arbitrary_model_selection() -> None:
    assert initial_model_role(context("complex_incident")) == ITModelRole.REASONING
    assert requires_reasoning_pass(valid_it_result(confidence="low"), ITModelRole.FAST) is True
