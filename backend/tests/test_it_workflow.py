from app.core.enums import DepartmentType
from app.departments.it.agent import ITDepartmentAgent
from app.departments.registry import build_default_department_registry
from app.departments.customer_support.agent import CustomerSupportDepartmentAgent
from app.departments.base import DeterministicPlaceholderDepartmentAgent


def test_registry_has_real_customer_support_it_and_finance() -> None:
    registry = build_default_department_registry()
    assert isinstance(registry.resolve(DepartmentType.CUSTOMER_SUPPORT), CustomerSupportDepartmentAgent)
    assert isinstance(registry.resolve(DepartmentType.IT), ITDepartmentAgent)
    assert not isinstance(
        registry.resolve(DepartmentType.FINANCE),
        DeterministicPlaceholderDepartmentAgent,
    )
    for department in (DepartmentType.HR, DepartmentType.PROCUREMENT):
        assert isinstance(registry.resolve(department), DeterministicPlaceholderDepartmentAgent)
