from uuid import uuid4

from app.departments.contracts import DepartmentCollaborationResult
from app.requests.enums import RequestStatus
from app.workflow.routing import route_after_collaboration
from app.workflow.state import build_initial_workflow_state
from app.requests.models import BusinessRequest


def test_hr_it_result_routes_back_to_hr_execution() -> None:
    request = BusinessRequest(id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        request_type="onboarding", title="Onboard", summary="Prepare onboarding",
        status=RequestStatus.CREATED, current_stage="created")
    state = build_initial_workflow_state(request)
    result = DepartmentCollaborationResult(request_id=request.id, sender_department="hr", receiver_department="it",
        action="prepare_employee_onboarding_it", status="completed", result={"prepared": True}, reason="Prepared")
    state = state.model_copy(update={"collaboration": state.collaboration.model_copy(update={"structured_result": result.model_dump(mode="json")})})
    assert route_after_collaboration(state) == "department_execution"
