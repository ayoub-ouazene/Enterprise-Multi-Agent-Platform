from collections.abc import Iterable

from app.core.enums import DepartmentType
from app.departments.base import DepartmentAgent
from app.departments.customer_support.agent import CustomerSupportDepartmentAgent
from app.departments.exceptions import (
    DepartmentImplementationNotFoundError,
    DuplicateDepartmentRegistrationError,
)
from app.departments.finance.agent import FinanceDepartmentAgent
from app.departments.hr.agent import HRDepartmentAgent
from app.departments.it.agent import ITDepartmentAgent
from app.departments.procurement.agent import ProcurementDepartmentAgent


class DepartmentRegistry:
    """Deterministic, replaceable mapping from department type to implementation."""

    def __init__(self, agents: Iterable[DepartmentAgent] = ()) -> None:
        self._agents: dict[DepartmentType, DepartmentAgent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: DepartmentAgent) -> None:
        department_type = agent.department_type
        if department_type in self._agents:
            raise DuplicateDepartmentRegistrationError(
                f"An implementation is already registered for {department_type.value}"
            )
        self._agents[department_type] = agent

    def resolve(self, department_type: DepartmentType) -> DepartmentAgent:
        try:
            return self._agents[department_type]
        except KeyError:
            raise DepartmentImplementationNotFoundError(
                "No implementation is registered for the active department"
            ) from None

    @property
    def registered_types(self) -> tuple[DepartmentType, ...]:
        return tuple(sorted(self._agents, key=lambda item: item.value))


def build_default_department_registry(
    customer_support_agent: CustomerSupportDepartmentAgent | None = None,
    it_agent: ITDepartmentAgent | None = None,
) -> DepartmentRegistry:
    return DepartmentRegistry(
        (
            customer_support_agent or CustomerSupportDepartmentAgent(),
            HRDepartmentAgent(),
            it_agent or ITDepartmentAgent(),
            FinanceDepartmentAgent(),
            ProcurementDepartmentAgent(),
        )
    )
