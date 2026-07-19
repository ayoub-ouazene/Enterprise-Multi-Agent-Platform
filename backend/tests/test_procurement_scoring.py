from decimal import Decimal
from uuid import UUID

import pytest

from app.departments.procurement.enums import AvailabilityStatus, ComplianceStatus
from app.departments.procurement.scoring import (
    CandidateFacts,
    ProcurementCalculationError,
    calculate_total_cost,
    evaluate_and_rank,
    validate_weights,
)


WEIGHTS = {
    "price": Decimal("0.400"),
    "quality": Decimal("0.300"),
    "delivery": Decimal("0.200"),
    "compliance": Decimal("0.100"),
}


def candidate(
    value: int,
    *,
    cost: str,
    quality: str = "80.000",
    days: int = 5,
    currency: str = "USD",
    specification: bool = True,
    compliance: ComplianceStatus = ComplianceStatus.ELIGIBLE,
) -> CandidateFacts:
    return CandidateFacts(
        id=UUID(int=value),
        supplier_name=f"Supplier {value}",
        total_cost=Decimal(cost),
        currency=currency,
        delivery_days=days,
        quality_score=Decimal(quality),
        meets_minimum_specification=specification,
        compliance_status=compliance,
        availability_status=AvailabilityStatus.AVAILABLE,
    )


def test_total_cost_uses_exact_decimal_tax_and_delivery() -> None:
    assert calculate_total_cost("19.99", "3.000", "5.00", "2.50") == Decimal(
        "67.47"
    )


@pytest.mark.parametrize("value", ["-1.00", -1, 1.001])
def test_invalid_money_is_rejected(value) -> None:
    with pytest.raises(ProcurementCalculationError):
        calculate_total_cost(value, "1.000")


def test_weights_must_sum_exactly_to_one() -> None:
    with pytest.raises(ProcurementCalculationError, match="sum exactly"):
        validate_weights({**WEIGHTS, "price": Decimal("0.399")})


def test_price_and_weighted_scores_are_deterministic() -> None:
    records = [candidate(2, cost="200.00"), candidate(1, cost="100.00")]
    first = evaluate_and_rank(records, WEIGHTS)
    second = evaluate_and_rank(list(reversed(records)), WEIGHTS)

    assert [(item.candidate_id, item.rank) for item in first] == [
        (UUID(int=1), 1),
        (UUID(int=2), 2),
    ]
    assert first == second
    assert first[0].price_score == Decimal("100.000")
    assert first[1].price_score == Decimal("50.000")


def test_tie_breaks_by_cost_delivery_name_and_uuid() -> None:
    records = [
        candidate(2, cost="100.00", days=2),
        candidate(1, cost="100.00", days=2),
    ]
    ranked = evaluate_and_rank(records, WEIGHTS)
    assert [item.candidate_id for item in ranked] == [UUID(int=1), UUID(int=2)]


def test_ineligible_and_minimum_specification_failures_are_excluded() -> None:
    records = [
        candidate(1, cost="100.00", specification=False),
        candidate(2, cost="90.00", compliance=ComplianceStatus.INELIGIBLE),
    ]
    result = evaluate_and_rank(records, WEIGHTS)
    assert all(not item.eligible and item.rank is None for item in result)


def test_mixed_currencies_are_not_ranked() -> None:
    with pytest.raises(ProcurementCalculationError, match="different currencies"):
        evaluate_and_rank(
            [candidate(1, cost="100.00"), candidate(2, cost="90.00", currency="EUR")],
            WEIGHTS,
        )
