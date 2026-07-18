from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.schemas import WorkflowEventCreate


def event_payload(**overrides):
    values = {
        "event_type": WorkflowEventType.REQUEST_CREATED,
        "stage": "request_received",
        "title": "Request created",
        "message": "The request has been created.",
        "actor_type": WorkflowEventActorType.USER,
        "department_id": uuid4(),
        "visibility": WorkflowEventVisibility.REQUESTER,
        "event_data": {},
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "event_data",
    [
        {"api_key": "secret"},
        {"nested": {"database_url": "postgresql://private"}},
        {"raw_tool_output": "unrestricted output"},
        {"chain_of_thought": "hidden reasoning"},
        {"traceback": "private stack"},
    ],
)
def test_event_data_rejects_prohibited_keys(event_data) -> None:
    with pytest.raises(ValidationError):
        WorkflowEventCreate(**event_payload(event_data=event_data))


def test_event_type_rejects_arbitrary_strings() -> None:
    with pytest.raises(ValidationError):
        WorkflowEventCreate(**event_payload(event_type="temporary_department_message"))


def test_event_input_rejects_trusted_identity_fields() -> None:
    with pytest.raises(ValidationError):
        WorkflowEventCreate(**event_payload(company_id=uuid4(), actor_user_id=uuid4()))
