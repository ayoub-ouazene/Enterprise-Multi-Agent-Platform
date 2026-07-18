from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from app.companies.models import Company
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.departments.models import Department
from app.departments.schemas import DepartmentCreate
from app.employees.models import Employee
from app.users.models import User


def constraint_names(model) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if constraint.name is not None
    }


def test_foundational_models_can_be_created() -> None:
    company_id = uuid4()
    user_id = uuid4()
    department_id = uuid4()
    manager_id = uuid4()

    company = Company(
        id=company_id,
        name="Example Company",
        slug="example-company",
        is_active=True,
        custom_data={"region": "west"},
    )
    user = User(
        id=user_id,
        company_id=company_id,
        email="employee@example.com",
        actor_type=ActorType.EMPLOYEE,
        is_active=True,
    )
    department = Department(
        id=department_id,
        company_id=company_id,
        name="Information Technology",
        department_type=DepartmentType.IT,
        is_active=True,
        custom_data={},
    )
    employee = Employee(
        id=uuid4(),
        company_id=company_id,
        user_id=user_id,
        department_id=department_id,
        employee_code="EMP-001",
        manager_employee_id=manager_id,
        employment_status=EmploymentStatus.ACTIVE,
        custom_data={},
    )

    assert company.id == company_id
    assert user.company_id == company_id
    assert department.department_type is DepartmentType.IT
    assert employee.manager_employee_id == manager_id


def test_relationships_match_the_foundational_domain() -> None:
    assert set(inspect(Company).relationships.keys()) == {
        "users",
        "departments",
        "employees",
    }
    assert set(inspect(User).relationships.keys()) == {"company", "employee"}
    assert set(inspect(Department).relationships.keys()) == {"company", "employees"}
    assert set(inspect(Employee).relationships.keys()) == {
        "company",
        "user",
        "department",
        "manager",
        "subordinates",
    }


def test_unique_constraints_are_declared() -> None:
    assert "uq_companies_slug" in constraint_names(Company)
    assert "uq_users_company_email" in constraint_names(User)
    assert "uq_departments_company_type" in constraint_names(Department)
    assert "uq_employees_company_code" in constraint_names(Employee)
    assert "uq_employees_user_id" in constraint_names(Employee)


def test_unsupported_department_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DepartmentCreate(
            name="Legal",
            department_type="legal",
        )
