from app.core.enums import DepartmentType
from app.departments.finance.agent import FinanceDepartmentAgent
from app.departments.hr.agent import HRDepartmentAgent
from app.departments.procurement.agent import ProcurementDepartmentAgent
from app.departments.registry import build_default_department_registry
from app.workflow.graph import workflow_graph


def test_registry_has_three_real_and_two_placeholder_departments() -> None:
    registry = build_default_department_registry()
    assert isinstance(registry.resolve(DepartmentType.FINANCE), FinanceDepartmentAgent)
    assert isinstance(registry.resolve(DepartmentType.HR), HRDepartmentAgent)
    assert isinstance(registry.resolve(DepartmentType.PROCUREMENT), ProcurementDepartmentAgent)
    assert registry.resolve(DepartmentType.CUSTOMER_SUPPORT).__class__.__name__ == "CustomerSupportDepartmentAgent"
    assert registry.resolve(DepartmentType.IT).__class__.__name__ == "ITDepartmentAgent"


def test_central_graph_still_compiles_with_finance_nodes() -> None:
    assert workflow_graph is not None
