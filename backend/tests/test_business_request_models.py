from sqlalchemy import inspect

from app.database import models as database_models
from app.requests.enums import (
    TERMINAL_REQUEST_STATUSES,
    RequestPriority,
    RequestStatus,
)
from app.requests.models import BusinessRequest


def test_business_request_model_has_required_fields_and_relationships() -> None:
    mapper = inspect(BusinessRequest)
    columns = set(mapper.columns.keys())
    relationships = set(mapper.relationships.keys())

    assert {
        "id",
        "company_id",
        "requester_user_id",
        "requester_employee_id",
        "owner_department_id",
        "active_department_id",
        "request_type",
        "title",
        "summary",
        "status",
        "current_stage",
        "priority",
        "workflow_state",
        "custom_data",
        "final_decision",
        "final_reason",
        "created_at",
        "updated_at",
        "completed_at",
        "cancelled_at",
        "failed_at",
    } == columns
    assert {
        "company",
        "requester_user",
        "requester_employee",
        "owner_department",
        "active_department",
    } == relationships
    assert database_models.BusinessRequest is BusinessRequest


def test_request_enums_are_closed_and_terminal_values_are_explicit() -> None:
    assert [item.value for item in RequestPriority] == [
        "low",
        "normal",
        "high",
        "urgent",
    ]
    assert RequestStatus.COMPLETED in TERMINAL_REQUEST_STATUSES
    assert RequestStatus.REJECTED in TERMINAL_REQUEST_STATUSES
    assert RequestStatus.CANCELLED in TERMINAL_REQUEST_STATUSES
    assert RequestStatus.FAILED in TERMINAL_REQUEST_STATUSES
