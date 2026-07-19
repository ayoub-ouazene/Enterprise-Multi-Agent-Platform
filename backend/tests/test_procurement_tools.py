import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.departments.contracts import DepartmentToolRequest
from app.departments.procurement.enums import AvailabilityStatus, ComplianceStatus
from app.departments.procurement.tools import ProcurementOperationError, ProcurementToolService


def candidate(value: int, cost: str):
    return SimpleNamespace(
        id=UUID(int=value), supplier_name=f"Supplier {value}",
        total_cost=Decimal(cost), currency="USD", delivery_days=2,
        quality_score=Decimal("80.000"), meets_minimum_specification=True,
        compliance_status=ComplianceStatus.ELIGIBLE,
        availability_status=AvailabilityStatus.AVAILABLE,
        quoted_unit_price=Decimal(cost), quantity=Decimal("1.000"),
        delivery_cost=Decimal("0.00"), tax_amount=None,
        price_score=None, delivery_score=None, compliance_score=None,
        overall_score=None, rank=None, evaluation_reason=None,
        is_shortlisted=False,
    )


def request(operation, arguments):
    return DepartmentToolRequest(
        tool_name="procurement", operation=operation, arguments=arguments,
        reason="Deterministic evaluation required.", expected_result_type="object",
    )


def test_create_shortlist_persists_only_eligible_top_candidates() -> None:
    repository = AsyncMock()
    repository.session = AsyncMock()
    repository.list_for_request.return_value = [candidate(2, "200.00"), candidate(1, "100.00")]
    service = ProcurementToolService(repository, request_id=UUID(int=9))
    output = asyncio.run(service.execute(request("create_shortlist", {
        "weights": {"price": "0.400", "quality": "0.300", "delivery": "0.200", "compliance": "0.100"},
        "shortlist_size": 1,
    })))
    assert output["eligible_candidate_count"] == 2
    assert sum(item["shortlisted"] for item in output["rankings"]) == 1
    assert repository.list_for_request.await_args.kwargs["for_update"] is True


def test_unapproved_procurement_operation_is_rejected() -> None:
    service = ProcurementToolService(AsyncMock(), request_id=UUID(int=1))
    with pytest.raises(ProcurementOperationError):
        asyncio.run(service.execute(request("execute_purchase", {})))
