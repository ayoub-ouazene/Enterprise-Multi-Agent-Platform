from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentConfidence, DepartmentNextAction
from app.departments.procurement.enums import (
    ComplianceStatus,
    ProcurementDecision,
    ProcurementRequestCategory,
)
from app.departments.procurement.schemas import (
    ProcurementCandidateSummary,
    ProcurementDepartmentResult,
)


def base(**updates):
    values = dict(
        category=ProcurementRequestCategory.SHORTLIST_GENERATION,
        decision=ProcurementDecision.SHORTLIST_READY,
        reason="Candidates were scored deterministically.",
        user_message="A shortlist is ready; no purchase was executed.",
        confidence=DepartmentConfidence.HIGH,
        requirements_complete=True,
        candidate_count=1,
        eligible_candidate_count=1,
        shortlist=[],
        next_action=DepartmentNextAction.COMPLETE_REQUEST,
        safe_event_title="Shortlist ready",
        safe_event_message="Procurement prepared a supplier shortlist.",
    )
    values.update(updates)
    return values


def summary(candidate_id=None):
    return ProcurementCandidateSummary(
        candidate_id=candidate_id or uuid4(), supplier_name="Supplier A",
        total_cost=Decimal("100.00"), currency="usd", delivery_days=3,
        compliance_status=ComplianceStatus.ELIGIBLE,
        overall_score=Decimal("92.500"), rank=1,
        recommendation_reason="Highest deterministic score.",
    )


def test_recommendation_must_reference_shortlist() -> None:
    with pytest.raises(ValidationError, match="eligible shortlist"):
        ProcurementDepartmentResult(**base(recommended_candidate_id=uuid4(), recommendation_reason="Best"))


def test_finance_flag_requires_typed_collaboration() -> None:
    with pytest.raises(ValidationError, match="Finance collaboration"):
        ProcurementDepartmentResult(**base(
            requires_finance_collaboration=True,
            next_action=DepartmentNextAction.COLLABORATE,
        ))


def test_purchase_execution_prohibition_cannot_be_disabled() -> None:
    with pytest.raises(ValidationError):
        ProcurementDepartmentResult(**base(purchase_execution_prohibited=False))


def test_purchase_execution_claim_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot claim"):
        ProcurementDepartmentResult(**base(user_message="Purchase completed."))


def test_valid_recommendation_is_advisory() -> None:
    item = summary()
    result = ProcurementDepartmentResult(**base(
        shortlist=[item], recommended_candidate_id=item.candidate_id,
        recommendation_reason="Highest eligible score.",
    ))
    assert result.recommended_candidate_id == item.candidate_id
    assert result.purchase_execution_prohibited is True


def test_finance_request_preserves_request_id_and_departments() -> None:
    request_id = uuid4()
    result = ProcurementDepartmentResult(**base(
        requires_finance_collaboration=True,
        finance_collaboration_request={
            "request_id": request_id,
            "sender_department": DepartmentType.PROCUREMENT,
            "receiver_department": DepartmentType.FINANCE,
            "action": "validate_procurement_purchase",
            "payload": {}, "expected_output": {},
        },
        next_action=DepartmentNextAction.COLLABORATE,
    ))
    assert result.finance_collaboration_request.request_id == request_id
