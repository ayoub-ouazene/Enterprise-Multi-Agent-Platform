from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.sanitization import DEFAULT_SAFE_FAILURE_MESSAGE
from app.failures.enums import FailureSource, FailureType
from app.failures.schemas import CapabilityGapCreate, FailureCreate


def failure_payload(**overrides):
    values = {
        "failure_type": FailureType.DATABASE_FAILURE,
        "failure_source": FailureSource.REPOSITORY,
        "failed_operation": "read_inventory",
        "internal_message": "database password=private",
        "safe_message": "Traceback: SELECT * FROM assets",
        "technical_data": {},
    }
    values.update(overrides)
    return values


def test_failure_messages_are_sanitized_and_separated() -> None:
    payload = FailureCreate(**failure_payload())
    assert "private" not in payload.internal_message
    assert payload.safe_message == DEFAULT_SAFE_FAILURE_MESSAGE
    assert payload.internal_message != payload.safe_message


@pytest.mark.parametrize(
    "data", [{"api_key": "x"}, {"traceback": "x"}, {"nested": {"password": "x"}}]
)
def test_failure_technical_data_rejects_secrets(data) -> None:
    with pytest.raises(ValidationError):
        FailureCreate(**failure_payload(technical_data=data))


def test_capability_gap_sanitizes_messages_and_rejects_client_company() -> None:
    with pytest.raises(ValidationError):
        CapabilityGapCreate(
            requested_operation="Export data",
            description="secret=private",
            safe_user_message="Safe message",
            company_id=uuid4(),
        )
    gap = CapabilityGapCreate(
        requested_operation="Export data",
        description="api_key=private",
        safe_user_message="Safe message",
    )
    assert "private" not in gap.description
