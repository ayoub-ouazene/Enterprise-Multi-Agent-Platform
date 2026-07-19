import pytest

from app.core.enums import DepartmentType
from app.departments.exceptions import (
    DepartmentImplementationNotFoundError,
    DuplicateDepartmentRegistrationError,
)
from app.departments.it.agent import ITDepartmentAgent
from app.departments.finance.agent import FinanceDepartmentAgent
from app.departments.registry import (
    DepartmentRegistry,
    build_default_department_registry,
)


def test_default_registry_contains_all_five_departments() -> None:
    registry = build_default_department_registry()

    assert registry.registered_types == tuple(
        sorted(DepartmentType, key=lambda item: item.value)
    )
    for department_type in DepartmentType:
        assert registry.resolve(department_type).department_type == department_type
    assert isinstance(registry.resolve(DepartmentType.FINANCE), FinanceDepartmentAgent)


def test_duplicate_registration_is_rejected() -> None:
    registry = DepartmentRegistry([ITDepartmentAgent()])

    with pytest.raises(DuplicateDepartmentRegistrationError, match="already registered"):
        registry.register(ITDepartmentAgent())


def test_unsupported_lookup_fails_without_fallback() -> None:
    registry = DepartmentRegistry()

    with pytest.raises(DepartmentImplementationNotFoundError):
        registry.resolve(DepartmentType.IT)
