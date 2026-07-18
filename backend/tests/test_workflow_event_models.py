from sqlalchemy import CheckConstraint, UniqueConstraint, inspect

from app.database import models as database_models
from app.workflow.enums import (
    WorkflowEventActorType,
    WorkflowEventType,
    WorkflowEventVisibility,
)
from app.workflow.models import WorkflowEvent


def test_workflow_event_model_has_required_fields_and_relationships() -> None:
    mapper = inspect(WorkflowEvent)

    assert set(mapper.columns.keys()) == {
        "id",
        "company_id",
        "request_id",
        "event_type",
        "stage",
        "title",
        "message",
        "actor_type",
        "actor_user_id",
        "department_id",
        "visibility",
        "event_data",
        "sequence_number",
        "created_at",
    }
    assert set(mapper.relationships.keys()) == {
        "company",
        "business_request",
        "actor_user",
        "department",
    }
    assert database_models.WorkflowEvent is WorkflowEvent


def test_workflow_event_sequence_constraints_are_declared() -> None:
    constraints = WorkflowEvent.__table__.constraints

    assert any(
        isinstance(item, UniqueConstraint)
        and item.name == "uq_workflow_events_request_sequence"
        for item in constraints
    )
    assert any(
        isinstance(item, CheckConstraint)
        and item.name == "ck_workflow_events_positive_sequence"
        for item in constraints
    )


def test_workflow_event_enums_are_closed() -> None:
    assert {item.value for item in WorkflowEventVisibility} == {
        "requester",
        "manager",
        "company",
        "internal",
    }
    assert {item.value for item in WorkflowEventActorType} == {
        "system",
        "router",
        "department_agent",
        "reviewer",
        "user",
        "manager",
        "company_account",
        "tool",
    }
    assert WorkflowEventType.REQUEST_CREATED.value == "request_created"
    assert WorkflowEventType.REQUEST_FAILED.value == "request_failed"
    assert WorkflowEventType.FAILURE_RECORDED.value == "failure_recorded"
    assert WorkflowEventType.CAPABILITY_GAP_DETECTED.value == "capability_gap_detected"
