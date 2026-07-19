from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.workflow.collaboration.schemas import (
    DiagnoseExternalTechnicalIssueRequest,
    DiagnoseExternalTechnicalIssueResult,
    FindITAssetSuppliersRequest,
    FindITAssetSuppliersResult,
    PrepareEmployeeOnboardingITRequest,
    PrepareEmployeeOnboardingITResult,
    ValidateITPurchaseBudgetRequest,
    ValidateITPurchaseBudgetResult,
    ValidateProcurementPurchaseRequest,
    ValidateProcurementPurchaseResult,
)


def test_all_action_request_and_result_schemas_are_strict_and_typed() -> None:
    pairs = (
        (
            DiagnoseExternalTechnicalIssueRequest(issue_summary="Portal unavailable"),
            DiagnoseExternalTechnicalIssueResult(
                diagnosis_status="diagnosed",
                internal_resolution_summary="A safe configuration issue was identified.",
                safe_customer_support_response="Please retry after refreshing your session.",
            ),
        ),
        (
            ValidateITPurchaseBudgetRequest(
                asset_or_software="Laptop", estimated_cost=Decimal("1200.00"),
                currency="usd", business_reason="New employee equipment",
            ),
            ValidateITPurchaseBudgetResult(
                finance_decision="validated", validated_amount=Decimal("1200.00"),
                currency="USD", budget_sufficient=True, reason="Budget is available.",
            ),
        ),
        (
            FindITAssetSuppliersRequest(
                asset_or_software="Laptop", currency="USD", required_by_date=date(2027, 1, 1),
            ),
            FindITAssetSuppliersResult(
                eligible_candidate_count=0, reason="No eligible candidates were found.",
            ),
        ),
        (
            ValidateProcurementPurchaseRequest(
                candidate_reference="supplier-1", total_amount=Decimal("99.99"),
                currency="USD", business_reason="Approved equipment requirement",
            ),
            ValidateProcurementPurchaseResult(
                finance_decision="validated", validated_amount=Decimal("99.99"),
                currency="USD", budget_sufficient=True, reason="Budget is available.",
            ),
        ),
        (
            PrepareEmployeeOnboardingITRequest(
                employee_id=uuid4(), role_title="Engineer", required_systems=["email"],
            ),
            PrepareEmployeeOnboardingITResult(readiness_status="prepared"),
        ),
    )
    assert len(pairs) == 5
    assert pairs[1][0].currency == "USD"
    with pytest.raises(ValidationError):
        DiagnoseExternalTechnicalIssueRequest(
            issue_summary="Portal unavailable", password="secret"  # type: ignore[call-arg]
        )
