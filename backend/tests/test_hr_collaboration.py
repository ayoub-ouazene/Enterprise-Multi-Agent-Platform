from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest


def test_hr_it_onboarding_collaboration_preserves_request_id() -> None:
    from uuid import uuid4
    request_id = uuid4()
    message = DepartmentCollaborationRequest(request_id=request_id, sender_department="hr",
        receiver_department="it", action="prepare_employee_onboarding_it",
        payload={"employee_id": str(uuid4()), "required_systems": ["email"]},
        expected_output={"prepared_actions": "list"})
    assert message.request_id == request_id
    assert message.sender_department == DepartmentType.HR
    assert message.receiver_department == DepartmentType.IT
