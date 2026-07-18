import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.requests.enums import RequestStatus
from app.workflow.state import (
    STATE_VERSION,
    WorkflowExecutionState,
    WorkflowState,
    build_initial_workflow_state,
)


def request_record(**overrides):
    values = {
        "id": uuid4(),
        "company_id": uuid4(),
        "requester_user_id": uuid4(),
        "requester_employee_id": uuid4(),
        "request_type": "test_it_request",
        "owner_department_id": None,
        "active_department_id": None,
        "status": RequestStatus.CREATED,
        "current_stage": "request_received",
        "summary": "Install approved software.",
        "workflow_state": {},
        "completed_at": None,
        "created_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_initial_state_is_derived_from_business_request() -> None:
    request = request_record()
    state = build_initial_workflow_state(request)

    assert state.state_version == STATE_VERSION
    assert state.request.request_id == request.id
    assert state.request.company_id == request.company_id
    assert state.request.requester_user_id == request.requester_user_id
    assert state.request.owner_department_id is None
    assert state.request.active_department_id is None
    assert state.request.status == RequestStatus.CREATED
    assert state.request.current_stage == "request_received"
    assert state.planning.completed_steps == []
    assert state.collaboration.is_active is False
    assert state.review.required is False
    assert state.human_action.required is False
    assert state.failure.has_failure is False
    assert state.result.completed_at is None


def test_state_storage_is_json_serializable() -> None:
    storage = build_initial_workflow_state(request_record()).to_storage()

    encoded = json.dumps(storage)

    assert '"state_version": 1' in encoded


def test_state_rejects_secret_keys() -> None:
    state = build_initial_workflow_state(request_record())
    payload = state.model_dump(mode="python")
    payload["execution"] = {"tool_results": [{"api_key": "secret"}]}

    with pytest.raises(ValidationError, match="forbidden sensitive key"):
        WorkflowState.model_validate(payload)


@pytest.mark.parametrize(
    "secret_value",
    [
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signaturevalue",
        "postgresql://user:password@example.com/database",
        "-----BEGIN PRIVATE KEY-----\nsecret",
    ],
)
def test_state_rejects_secret_like_values(secret_value: str) -> None:
    state = build_initial_workflow_state(request_record())
    payload = state.model_dump(mode="python")
    payload["execution"] = WorkflowExecutionState(
        tool_results=[{"summary": secret_value}]
    )

    with pytest.raises(ValidationError, match="secret-like value"):
        WorkflowState.model_validate(payload)


def test_state_rejects_unserializable_objects() -> None:
    state = build_initial_workflow_state(request_record())
    payload = state.model_dump(mode="python")
    payload["collaboration"]["payload"] = {"object": object()}

    with pytest.raises(ValidationError):
        WorkflowState.model_validate(payload)
