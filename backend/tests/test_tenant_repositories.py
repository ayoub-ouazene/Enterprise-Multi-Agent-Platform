import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.departments.repository import DepartmentRepository
from app.employees.repository import EmployeeRepository
from app.users.repository import UserRepository


def compiled_statement(session: AsyncMock) -> tuple[str, dict[str, object]]:
    statement = session.scalar.await_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    return str(compiled), compiled.params


def assert_company_scope(
    sql: str,
    params: dict[str, object],
    table_name: str,
    company_id: UUID,
) -> None:
    assert f"{table_name}.company_id =" in sql
    assert company_id in params.values()


def test_company_scoped_user_lookup() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = UserRepository(session, company_id)

    result = asyncio.run(repository.get_by_id(uuid4()))

    sql, params = compiled_statement(session)
    assert result is None
    assert_company_scope(sql, params, "users", company_id)


def test_company_scoped_department_lookup() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = DepartmentRepository(session, company_id)

    result = asyncio.run(repository.get_by_id(uuid4()))

    sql, params = compiled_statement(session)
    assert result is None
    assert_company_scope(sql, params, "departments", company_id)


def test_company_scoped_employee_lookup() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = EmployeeRepository(session, company_id)

    result = asyncio.run(repository.get_by_id(uuid4()))

    sql, params = compiled_statement(session)
    assert result is None
    assert_company_scope(sql, params, "employees", company_id)


def test_cross_company_record_access_behaves_as_not_found() -> None:
    active_company_id = uuid4()
    other_company_record_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = EmployeeRepository(session, active_company_id)

    result = asyncio.run(repository.get_by_id(other_company_record_id))

    sql, params = compiled_statement(session)
    assert result is None
    assert other_company_record_id in params.values()
    assert_company_scope(sql, params, "employees", active_company_id)


def test_tenant_owned_inserts_use_repository_company_id() -> None:
    company_id = uuid4()
    session = AsyncMock(spec=AsyncSession)

    user_repository = UserRepository(session, company_id)
    user = asyncio.run(
        user_repository.create(
            email="employee@example.com",
            actor_type=ActorType.EMPLOYEE,
            is_active=True,
        )
    )
    assert user.company_id == company_id

    department_repository = DepartmentRepository(session, company_id)
    department = asyncio.run(
        department_repository.create(
            name="Finance",
            department_type=DepartmentType.FINANCE,
            is_active=True,
            custom_data={},
        )
    )
    assert department.company_id == company_id

    employee_repository = EmployeeRepository(session, company_id)
    employee = asyncio.run(
        employee_repository.create(
            user_id=None,
            department_id=None,
            employee_code="EMP-001",
            job_title=None,
            manager_employee_id=None,
            employment_status=EmploymentStatus.ACTIVE,
            custom_data={},
        )
    )
    assert employee.company_id == company_id


def test_tenant_owned_updates_and_deletes_include_company_scope() -> None:
    company_id = uuid4()
    employee_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = EmployeeRepository(session, company_id)

    asyncio.run(repository.update(employee_id, {"job_title": "Engineer"}))
    update_sql, update_params = compiled_statement(session)
    assert employee_id in update_params.values()
    assert_company_scope(update_sql, update_params, "employees", company_id)

    session.execute.return_value = Mock(rowcount=0)
    deleted = asyncio.run(repository.delete(employee_id))
    delete_statement = session.execute.await_args.args[0]
    compiled_delete = delete_statement.compile(dialect=postgresql.dialect())
    delete_sql = str(compiled_delete)
    delete_params = compiled_delete.params

    assert deleted is False
    assert employee_id in delete_params.values()
    assert_company_scope(delete_sql, delete_params, "employees", company_id)
