import pytest
from pydantic import ValidationError

from app.requests.schemas import BusinessRequestCreate


def valid_payload() -> dict[str, object]:
    return {
        "request_type": "software_access",
        "title": "Request access",
        "summary": "Access is needed for assigned work.",
    }


@pytest.mark.parametrize(
    "trusted_field",
    [
        "company_id",
        "requester_user_id",
        "requester_employee_id",
        "owner_department_id",
        "active_department_id",
        "status",
        "workflow_state",
        "final_decision",
        "final_reason",
    ],
)
def test_client_cannot_set_trusted_request_fields(trusted_field: str) -> None:
    payload = valid_payload()
    payload[trusted_field] = "client-controlled"

    with pytest.raises(ValidationError):
        BusinessRequestCreate.model_validate(payload)
