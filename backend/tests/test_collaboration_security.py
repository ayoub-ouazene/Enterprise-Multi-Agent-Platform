from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.enums import DepartmentType
from app.workflow.collaboration.exceptions import CollaborationValidationError
from app.workflow.collaboration.service import CollaborationService
from app.workflow.state import DepartmentRuntimeContext
from tests.test_collaboration_service import Executor, initial_state, settings


def test_collaboration_state_rejects_secret_bearing_payloads() -> None:
    state, _ = initial_state()
    state.collaboration.request["payload"] = {
        "issue_summary": "Portal unavailable",
        "password": "must-not-be-stored",
    }
    with pytest.raises(ValidationError):
        state.__class__.model_validate(state.model_dump(mode="json"))


def test_only_the_trusted_active_sender_can_start_collaboration() -> None:
    state, departments = initial_state()
    foreign_active_id = uuid4()
    state.request.active_department_id = foreign_active_id
    departments[DepartmentType.FINANCE] = DepartmentRuntimeContext(
        foreign_active_id, True
    )
    service = CollaborationService(settings(), Executor())
    with pytest.raises(CollaborationValidationError):
        service.prepare(state, departments)


def test_inactive_receiver_is_rejected_without_executing_it() -> None:
    state, departments = initial_state()
    departments[DepartmentType.IT] = DepartmentRuntimeContext(
        departments[DepartmentType.IT].department_id, False
    )
    executor = Executor()
    service = CollaborationService(settings(), executor)
    with pytest.raises(CollaborationValidationError):
        service.prepare(state, departments)
    assert executor.calls == 0
