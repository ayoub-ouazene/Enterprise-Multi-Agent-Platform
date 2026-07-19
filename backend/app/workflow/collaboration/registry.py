from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentCollaborationRequest
from app.workflow.collaboration.exceptions import CollaborationRouteError
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


@dataclass(frozen=True, slots=True)
class CollaborationDefinition:
    sender: DepartmentType
    receiver: DepartmentType
    action: str
    request_schema: type[BaseModel]
    result_schema: type[BaseModel]
    allow_nested: bool = False
    allow_human_pause: bool = True

    @property
    def key(self) -> tuple[DepartmentType, DepartmentType, str]:
        return self.sender, self.receiver, self.action

    def validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request_schema.model_validate(payload).model_dump(mode="json")

    def validate_result(self, result: dict[str, Any]) -> dict[str, Any]:
        return self.result_schema.model_validate(result).model_dump(mode="json")


class CollaborationRegistry:
    def __init__(self) -> None:
        self._definitions: dict[
            tuple[DepartmentType, DepartmentType, str], CollaborationDefinition
        ] = {}

    def register(self, definition: CollaborationDefinition) -> None:
        if definition.key in self._definitions:
            raise CollaborationRouteError("Duplicate collaboration route")
        self._definitions[definition.key] = definition

    def resolve(
        self,
        sender: DepartmentType,
        receiver: DepartmentType,
        action: str,
    ) -> CollaborationDefinition:
        definition = self._definitions.get((sender, receiver, action))
        if definition is None:
            raise CollaborationRouteError("Unsupported collaboration route")
        return definition

    def validate_request(
        self, request: DepartmentCollaborationRequest
    ) -> tuple[CollaborationDefinition, dict[str, Any]]:
        definition = self.resolve(
            request.sender_department,
            request.receiver_department,
            request.action,
        )
        return definition, definition.validate_payload(request.payload)

    def routes(self) -> tuple[CollaborationDefinition, ...]:
        return tuple(self._definitions.values())


def build_default_collaboration_registry() -> CollaborationRegistry:
    registry = CollaborationRegistry()
    for definition in (
        CollaborationDefinition(
            DepartmentType.CUSTOMER_SUPPORT,
            DepartmentType.IT,
            "diagnose_external_technical_issue",
            DiagnoseExternalTechnicalIssueRequest,
            DiagnoseExternalTechnicalIssueResult,
        ),
        CollaborationDefinition(
            DepartmentType.IT,
            DepartmentType.FINANCE,
            "validate_it_purchase_budget",
            ValidateITPurchaseBudgetRequest,
            ValidateITPurchaseBudgetResult,
        ),
        CollaborationDefinition(
            DepartmentType.IT,
            DepartmentType.PROCUREMENT,
            "find_it_asset_suppliers",
            FindITAssetSuppliersRequest,
            FindITAssetSuppliersResult,
            allow_nested=True,
        ),
        CollaborationDefinition(
            DepartmentType.PROCUREMENT,
            DepartmentType.FINANCE,
            "validate_procurement_purchase",
            ValidateProcurementPurchaseRequest,
            ValidateProcurementPurchaseResult,
        ),
        CollaborationDefinition(
            DepartmentType.HR,
            DepartmentType.IT,
            "prepare_employee_onboarding_it",
            PrepareEmployeeOnboardingITRequest,
            PrepareEmployeeOnboardingITResult,
        ),
    ):
        registry.register(definition)
    return registry
