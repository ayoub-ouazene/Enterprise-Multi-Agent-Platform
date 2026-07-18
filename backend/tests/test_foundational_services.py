import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DepartmentType, EmploymentStatus
from app.core.exceptions import ConflictError
from app.departments.models import Department
from app.departments.repository import DepartmentRepository
from app.departments.schemas import DepartmentCreate
from app.departments.service import DepartmentService
from app.employees.models import Employee
from app.employees.repository import EmployeeRepository
from app.employees.schemas import EmployeeCreate
from app.employees.service import EmployeeService
from app.users.repository import UserRepository


def employee_payload(code: str) -> EmployeeCreate:
    return EmployeeCreate(
        employee_code=code,
        employment_status=EmploymentStatus.ACTIVE,
    )


def employee_repository_mock() -> Mock:
    repository = Mock(spec=EmployeeRepository)
    repository.get_by_code = AsyncMock(return_value=None)
    repository.get_by_user_id = AsyncMock(return_value=None)
    repository.get_by_id = AsyncMock(return_value=None)
    repository.create = AsyncMock()
    return repository


def test_duplicate_department_type_inside_company_is_rejected() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    repository = Mock(spec=DepartmentRepository)
    repository.get_by_type = AsyncMock(
        return_value=Department(
            id=uuid4(),
            company_id=company_id,
            name="IT",
            department_type=DepartmentType.IT,
            is_active=True,
            custom_data={},
        )
    )
    service = DepartmentService(session, company_id, repository)

    with pytest.raises(ConflictError):
        asyncio.run(
            service.create(
                DepartmentCreate(
                    name="Duplicate IT",
                    department_type=DepartmentType.IT,
                )
            )
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_duplicate_employee_code_inside_company_is_rejected() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    repository = employee_repository_mock()
    repository.get_by_code.return_value = Employee(
        id=uuid4(),
        company_id=company_id,
        employee_code="EMP-001",
        employment_status=EmploymentStatus.ACTIVE,
        custom_data={},
    )
    service = EmployeeService(
        session,
        company_id,
        repository,
        Mock(spec=UserRepository),
        Mock(spec=DepartmentRepository),
    )

    with pytest.raises(ConflictError):
        asyncio.run(service.create(employee_payload("EMP-001")))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_same_employee_code_is_allowed_in_different_companies() -> None:
    first_company_id = uuid4()
    second_company_id = uuid4()
    first_session = AsyncMock(spec=AsyncSession)
    second_session = AsyncMock(spec=AsyncSession)
    first_repository = employee_repository_mock()
    second_repository = employee_repository_mock()
    first_repository.create.return_value = Employee(
        id=uuid4(),
        company_id=first_company_id,
        employee_code="EMP-001",
        employment_status=EmploymentStatus.ACTIVE,
        custom_data={},
    )
    second_repository.create.return_value = Employee(
        id=uuid4(),
        company_id=second_company_id,
        employee_code="EMP-001",
        employment_status=EmploymentStatus.ACTIVE,
        custom_data={},
    )

    first_service = EmployeeService(
        first_session,
        first_company_id,
        first_repository,
        Mock(spec=UserRepository),
        Mock(spec=DepartmentRepository),
    )
    second_service = EmployeeService(
        second_session,
        second_company_id,
        second_repository,
        Mock(spec=UserRepository),
        Mock(spec=DepartmentRepository),
    )

    first_employee = asyncio.run(first_service.create(employee_payload("EMP-001")))
    second_employee = asyncio.run(second_service.create(employee_payload("EMP-001")))

    assert first_employee.company_id == first_company_id
    assert second_employee.company_id == second_company_id
    first_session.commit.assert_awaited_once()
    second_session.commit.assert_awaited_once()


def test_service_rolls_back_when_repository_operation_fails() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    repository = employee_repository_mock()
    repository.create.side_effect = RuntimeError("simulated persistence failure")
    service = EmployeeService(
        session,
        company_id,
        repository,
        Mock(spec=UserRepository),
        Mock(spec=DepartmentRepository),
    )

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        asyncio.run(service.create(employee_payload("EMP-002")))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
