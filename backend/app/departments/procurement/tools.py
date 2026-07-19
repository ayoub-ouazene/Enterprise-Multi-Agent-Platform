from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.departments.contracts import DepartmentToolRequest
from app.departments.procurement.repository import SupplierCandidateRepository
from app.departments.procurement.scoring import (
    CandidateFacts,
    ProcurementCalculationError,
    calculate_total_cost,
    evaluate_and_rank,
)


class ProcurementOperationError(RuntimeError):
    """Raised when a non-allowlisted or malformed Procurement tool is requested."""


class CandidateArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: UUID


class RankingArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weights: dict[str, Decimal]
    shortlist_size: int = Field(default=3, ge=1, le=20)


class ProcurementToolService:
    """Allowlisted deterministic Procurement tools; callers control commits."""

    def __init__(
        self,
        candidates: SupplierCandidateRepository,
        *,
        request_id: UUID,
    ) -> None:
        self.candidates = candidates
        self.request_id = request_id

    async def execute(self, request: DepartmentToolRequest) -> dict[str, Any]:
        operation = request.operation
        if operation == "list_supplier_candidates":
            records = await self.candidates.list_for_request(self.request_id)
            return {
                "operation": operation,
                "candidate_count": len(records),
                "candidate_ids": [str(item.id) for item in records],
            }
        if operation == "calculate_candidate_total_cost":
            arguments = CandidateArguments.model_validate(request.arguments)
            candidate = await self._candidate(arguments.candidate_id)
            total = calculate_total_cost(
                candidate.quoted_unit_price,
                candidate.quantity,
                candidate.delivery_cost,
                candidate.tax_amount or Decimal("0.00"),
            )
            return {
                "operation": operation,
                "candidate_id": str(candidate.id),
                "total_cost": str(total),
                "currency": candidate.currency,
            }
        if operation in {
            "evaluate_supplier_eligibility",
            "score_supplier_candidates",
            "rank_supplier_candidates",
            "create_shortlist",
        }:
            arguments = RankingArguments.model_validate(request.arguments)
            records = await self.candidates.list_for_request(
                self.request_id,
                for_update=operation == "create_shortlist",
            )
            evaluations = evaluate_and_rank(
                [self._facts(item) for item in records], arguments.weights
            )
            if operation == "create_shortlist":
                by_id = {item.id: item for item in records}
                for evaluation in evaluations:
                    candidate = by_id[evaluation.candidate_id]
                    candidate.price_score = evaluation.price_score
                    candidate.delivery_score = evaluation.delivery_score
                    candidate.compliance_score = evaluation.compliance_score
                    candidate.overall_score = evaluation.overall_score
                    candidate.rank = evaluation.rank
                    candidate.evaluation_reason = evaluation.reason
                    candidate.is_shortlisted = bool(
                        evaluation.eligible
                        and evaluation.rank is not None
                        and evaluation.rank <= arguments.shortlist_size
                    )
                await self.candidates.session.flush()
            return {
                "operation": operation,
                "eligible_candidate_count": sum(item.eligible for item in evaluations),
                "rankings": [
                    {
                        "candidate_id": str(item.candidate_id),
                        "eligible": item.eligible,
                        "price_score": str(item.price_score) if item.price_score is not None else None,
                        "delivery_score": (
                            str(item.delivery_score)
                            if item.delivery_score is not None
                            else None
                        ),
                        "compliance_score": (
                            str(item.compliance_score)
                            if item.compliance_score is not None
                            else None
                        ),
                        "overall_score": (
                            str(item.overall_score)
                            if item.overall_score is not None
                            else None
                        ),
                        "rank": item.rank,
                        "shortlisted": bool(
                            item.eligible
                            and item.rank is not None
                            and item.rank <= arguments.shortlist_size
                        ),
                    }
                    for item in evaluations
                ],
            }
        raise ProcurementOperationError("Procurement tool operation is not allowlisted")

    async def _candidate(self, candidate_id: UUID):
        candidate = await self.candidates.get(candidate_id)
        if candidate is None or candidate.request_id != self.request_id:
            raise ProcurementCalculationError("supplier candidate not found")
        return candidate

    @staticmethod
    def _facts(candidate: Any) -> CandidateFacts:
        return CandidateFacts(
            id=candidate.id,
            supplier_name=candidate.supplier_name,
            total_cost=candidate.total_cost,
            currency=candidate.currency,
            delivery_days=candidate.delivery_days,
            quality_score=candidate.quality_score,
            meets_minimum_specification=candidate.meets_minimum_specification,
            compliance_status=candidate.compliance_status,
            availability_status=candidate.availability_status,
        )
