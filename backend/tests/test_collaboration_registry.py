import pytest

from app.core.enums import DepartmentType
from app.workflow.collaboration.exceptions import CollaborationRouteError
from app.workflow.collaboration.registry import (
    CollaborationDefinition,
    CollaborationRegistry,
    build_default_collaboration_registry,
)
from app.workflow.collaboration.schemas import (
    DiagnoseExternalTechnicalIssueRequest,
    DiagnoseExternalTechnicalIssueResult,
)


def test_default_registry_contains_only_the_five_approved_routes() -> None:
    registry = build_default_collaboration_registry()
    routes = {(item.sender, item.receiver, item.action) for item in registry.routes()}
    assert routes == {
        (DepartmentType.CUSTOMER_SUPPORT, DepartmentType.IT, "diagnose_external_technical_issue"),
        (DepartmentType.IT, DepartmentType.FINANCE, "validate_it_purchase_budget"),
        (DepartmentType.IT, DepartmentType.PROCUREMENT, "find_it_asset_suppliers"),
        (DepartmentType.PROCUREMENT, DepartmentType.FINANCE, "validate_procurement_purchase"),
        (DepartmentType.HR, DepartmentType.IT, "prepare_employee_onboarding_it"),
    }


def test_registry_rejects_unsupported_and_duplicate_routes() -> None:
    registry = CollaborationRegistry()
    definition = CollaborationDefinition(
        DepartmentType.CUSTOMER_SUPPORT,
        DepartmentType.IT,
        "diagnose_external_technical_issue",
        DiagnoseExternalTechnicalIssueRequest,
        DiagnoseExternalTechnicalIssueResult,
    )
    registry.register(definition)
    with pytest.raises(CollaborationRouteError):
        registry.register(definition)
    with pytest.raises(CollaborationRouteError):
        registry.resolve(DepartmentType.HR, DepartmentType.FINANCE, "read_salary")
