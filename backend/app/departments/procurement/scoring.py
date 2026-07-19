from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from app.departments.procurement.enums import (
    AvailabilityStatus,
    ComplianceStatus,
)


CENT = Decimal("0.01")
THREE_PLACES = Decimal("0.001")
HUNDRED = Decimal("100")
WEIGHT_TOTAL = Decimal("1.000")
CRITERIA = ("price", "quality", "delivery", "compliance")


class ProcurementCalculationError(ValueError):
    """Safe business-input error from deterministic Procurement calculations."""


def _decimal(value: Any, *, label: str) -> Decimal:
    if isinstance(value, float):
        raise ProcurementCalculationError(f"{label} cannot use floating-point values")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ProcurementCalculationError(f"{label} is invalid") from None
    if not result.is_finite():
        raise ProcurementCalculationError(f"{label} must be finite")
    return result


def money(value: Any, *, allow_zero: bool = True) -> Decimal:
    result = _decimal(value, label="money")
    if result < 0 or (not allow_zero and result == 0):
        raise ProcurementCalculationError("money must be nonnegative")
    if result != result.quantize(CENT):
        raise ProcurementCalculationError("money supports at most two decimal places")
    if len(result.as_tuple().digits) > 18:
        raise ProcurementCalculationError("money exceeds supported precision")
    return result


def quantity(value: Any) -> Decimal:
    result = _decimal(value, label="quantity")
    if result <= 0 or result != result.quantize(THREE_PLACES):
        raise ProcurementCalculationError(
            "quantity must be positive with at most three decimal places"
        )
    if len(result.as_tuple().digits) > 12:
        raise ProcurementCalculationError("quantity exceeds supported precision")
    return result


def normalize_currency(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ProcurementCalculationError("currency must be a three-letter code")
    return normalized


def calculate_total_cost(
    unit_price: Any,
    item_quantity: Any,
    delivery_cost: Any = Decimal("0.00"),
    tax_amount: Any = Decimal("0.00"),
) -> Decimal:
    total = (
        money(unit_price)
        * quantity(item_quantity)
        + money(delivery_cost)
        + money(tax_amount)
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    if total <= 0:
        raise ProcurementCalculationError("candidate total cost must be positive")
    return total


def validate_weights(values: dict[str, Any]) -> dict[str, Decimal]:
    if set(values) != set(CRITERIA):
        raise ProcurementCalculationError(
            "weights must contain price, quality, delivery, and compliance"
        )
    weights = {key: _decimal(values[key], label=f"{key} weight") for key in CRITERIA}
    if any(value < 0 or value > 1 for value in weights.values()):
        raise ProcurementCalculationError("weights must be between zero and one")
    if sum(weights.values(), Decimal("0")) != WEIGHT_TOTAL:
        raise ProcurementCalculationError("weights must sum exactly to 1.000")
    return weights


@dataclass(frozen=True, slots=True)
class CandidateFacts:
    id: UUID
    supplier_name: str
    total_cost: Decimal
    currency: str
    delivery_days: int | None
    quality_score: Decimal | None
    meets_minimum_specification: bool
    compliance_status: ComplianceStatus
    availability_status: AvailabilityStatus


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate_id: UUID
    eligible: bool
    price_score: Decimal | None
    quality_score: Decimal | None
    delivery_score: Decimal | None
    compliance_score: Decimal | None
    overall_score: Decimal | None
    rank: int | None
    reason: str


def candidate_is_eligible(candidate: CandidateFacts, weights: dict[str, Decimal]) -> bool:
    if not candidate.meets_minimum_specification:
        return False
    if candidate.compliance_status != ComplianceStatus.ELIGIBLE:
        return False
    if candidate.availability_status not in {
        AvailabilityStatus.AVAILABLE,
        AvailabilityStatus.LIMITED,
    }:
        return False
    if candidate.total_cost <= 0:
        return False
    if weights["quality"] > 0 and candidate.quality_score is None:
        return False
    if weights["delivery"] > 0 and candidate.delivery_days is None:
        return False
    return True


def evaluate_and_rank(
    candidates: list[CandidateFacts],
    raw_weights: dict[str, Any],
) -> list[CandidateEvaluation]:
    weights = validate_weights(raw_weights)
    eligible = [item for item in candidates if candidate_is_eligible(item, weights)]
    currencies = {normalize_currency(item.currency) for item in eligible}
    if len(currencies) > 1:
        raise ProcurementCalculationError(
            "eligible candidates with different currencies cannot be ranked"
        )
    if not eligible:
        return [
            CandidateEvaluation(
                item.id,
                False,
                None,
                item.quality_score,
                None,
                None,
                None,
                None,
                "Candidate is missing required eligibility or evaluation data",
            )
            for item in candidates
        ]

    lowest = min(item.total_cost for item in eligible)
    delivery_values = [
        item.delivery_days for item in eligible if item.delivery_days is not None
    ]
    fastest = min(delivery_values) if delivery_values else 0
    scored: list[tuple[CandidateFacts, CandidateEvaluation]] = []
    for item in eligible:
        price = ((lowest / item.total_cost) * HUNDRED).quantize(
            THREE_PLACES, rounding=ROUND_HALF_UP
        )
        delivery = (
            (Decimal(fastest + 1) / Decimal((item.delivery_days or 0) + 1)) * HUNDRED
        ).quantize(THREE_PLACES, rounding=ROUND_HALF_UP)
        quality = (item.quality_score or Decimal("0")).quantize(THREE_PLACES)
        if quality < 0 or quality > 100:
            raise ProcurementCalculationError("quality score must be between 0 and 100")
        compliance = HUNDRED.quantize(THREE_PLACES)
        overall = (
            price * weights["price"]
            + quality * weights["quality"]
            + delivery * weights["delivery"]
            + compliance * weights["compliance"]
        ).quantize(THREE_PLACES, rounding=ROUND_HALF_UP)
        scored.append(
            (
                item,
                CandidateEvaluation(
                    item.id,
                    True,
                    price,
                    quality,
                    delivery,
                    compliance,
                    overall,
                    None,
                    "Candidate satisfies minimum requirements and was scored deterministically",
                ),
            )
        )

    scored.sort(
        key=lambda pair: (
            -(pair[1].overall_score or Decimal("0")),
            pair[0].total_cost,
            pair[0].delivery_days if pair[0].delivery_days is not None else 2**31,
            pair[0].supplier_name.casefold(),
            str(pair[0].id),
        )
    )
    ranked = [
        replace(evaluation, rank=index)
        for index, (_, evaluation) in enumerate(scored, start=1)
    ]
    eligible_ids = {item.candidate_id for item in ranked}
    ranked.extend(
        CandidateEvaluation(
            item.id,
            False,
            None,
            item.quality_score,
            None,
            None,
            None,
            None,
            "Candidate is missing required eligibility or evaluation data",
        )
        for item in candidates
        if item.id not in eligible_ids
    )
    return ranked
