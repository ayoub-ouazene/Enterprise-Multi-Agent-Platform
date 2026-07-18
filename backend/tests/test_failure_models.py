from sqlalchemy import CheckConstraint, inspect

from app.database import models as database_models
from app.failures.models import CapabilityGap, FailureLog


def test_failure_log_fields_relationships_and_history_constraints() -> None:
    mapper = inspect(FailureLog)
    assert {
        "company_id",
        "request_id",
        "department_id",
        "failure_type",
        "failure_source",
        "internal_message",
        "safe_message",
        "technical_data",
        "is_terminal",
        "resolved",
        "created_at",
    } <= set(mapper.columns.keys())
    assert {"company", "business_request", "department", "resolved_by"} == set(
        mapper.relationships.keys()
    )
    assert any(
        isinstance(item, CheckConstraint) for item in FailureLog.__table__.constraints
    )
    assert database_models.FailureLog is FailureLog


def test_capability_gap_fields_relationships_and_dedup_index() -> None:
    mapper = inspect(CapabilityGap)
    assert {
        "normalized_operation",
        "deduplication_key",
        "occurrence_count",
        "first_seen_at",
        "last_seen_at",
        "gap_metadata",
    } <= set(mapper.columns.keys())
    assert mapper.columns["gap_metadata"].name == "metadata"
    assert any(
        index.name == "uq_capability_gaps_unresolved_dedup" and index.unique
        for index in CapabilityGap.__table__.indexes
    )
    assert database_models.CapabilityGap is CapabilityGap
