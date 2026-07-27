"""Idempotent, development-only demo identity seed.

Run from ``backend`` with:
    conda run -n dev python scripts/seed_demo.py

Passwords are requested interactively and are never logged or stored as plain text.
The command refuses to run outside development/test environments.
"""

import asyncio
from getpass import getpass

from app.auth.passwords import hash_password
from app.companies.repository import CompanyRepository
from app.companies.service import DEPARTMENT_NAMES
from app.core.config import AppEnvironment, get_settings
from app.core.enums import ActorType, DepartmentType, EmploymentStatus
from app.database import models as database_models
from app.database.session import create_database_engine, create_session_factory
from app.departments.repository import DepartmentRepository
from app.employees.repository import EmployeeRepository
from app.users.repository import UserRepository


_ = database_models
DEMO_SLUG = "tellus-demo"


async def _ensure_user(
    users: UserRepository,
    *,
    email: str,
    actor_type: ActorType,
    password_hash: str,
    must_change_password: bool,
):
    existing = await users.get_by_email(email)
    if existing is not None:
        existing.actor_type = actor_type
        existing.password_hash = password_hash
        existing.is_active = True
        existing.must_change_password = must_change_password
        return existing
    return await users.create(
        email=email,
        actor_type=actor_type,
        is_active=True,
        password_hash=password_hash,
        must_change_password=must_change_password,
    )


async def seed(password: str) -> None:
    settings = get_settings()
    if settings.app_env not in {
        AppEnvironment.DEVELOPMENT,
        AppEnvironment.TEST,
    }:
        raise SystemExit("Demo seeding is allowed only in development or test")

    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            companies = CompanyRepository(session)
            company = await companies.get_by_slug(DEMO_SLUG)
            if company is None:
                company = await companies.create(
                    {
                        "name": "TellUS Demo Company",
                        "slug": DEMO_SLUG,
                        "is_active": True,
                        "custom_data": {},
                    }
                )
            else:
                company.is_active = True

            departments = DepartmentRepository(session, company.id)
            department_ids = {}
            for department_type, name in DEPARTMENT_NAMES.items():
                department = await departments.get_by_type(department_type)
                if department is None:
                    department = await departments.create(
                        name=name,
                        department_type=department_type,
                        is_active=True,
                        custom_data={},
                    )
                else:
                    department.is_active = True
                department_ids[department_type] = department.id

            encoded = hash_password(password)
            users = UserRepository(session, company.id)
            await _ensure_user(
                users,
                email="company@tellus-demo.example.com",
                actor_type=ActorType.COMPANY,
                password_hash=encoded,
                must_change_password=False,
            )
            employee_user = await _ensure_user(
                users,
                email="employee@tellus-demo.example.com",
                actor_type=ActorType.EMPLOYEE,
                password_hash=encoded,
                must_change_password=True,
            )
            manager_user = await _ensure_user(
                users,
                email="manager@tellus-demo.example.com",
                actor_type=ActorType.DEPARTMENT_MANAGER,
                password_hash=encoded,
                must_change_password=False,
            )
            await _ensure_user(
                users,
                email="external@tellus-demo.example.com",
                actor_type=ActorType.EXTERNAL_USER,
                password_hash=encoded,
                must_change_password=False,
            )

            employees = EmployeeRepository(session, company.id)
            if await employees.get_by_user_id(manager_user.id) is None:
                await employees.create(
                    user_id=manager_user.id,
                    department_id=department_ids[DepartmentType.IT],
                    employee_code="DEMO-MGR",
                    job_title="IT Manager",
                    manager_employee_id=None,
                    employment_status=EmploymentStatus.ACTIVE,
                    custom_data={},
                )
            if await employees.get_by_user_id(employee_user.id) is None:
                await employees.create(
                    user_id=employee_user.id,
                    department_id=department_ids[DepartmentType.IT],
                    employee_code="DEMO-EMP",
                    job_title="Demo Employee",
                    manager_employee_id=None,
                    employment_status=EmploymentStatus.ACTIVE,
                    custom_data={},
                )
            await session.commit()
    finally:
        await engine.dispose()

    print(
        "Demo identities are ready in workspace 'tellus-demo'. "
        "Use the password entered for this command."
    )


def main() -> None:
    password = getpass("Demo password (12-128 characters): ")
    confirmation = getpass("Confirm demo password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")
    asyncio.run(seed(password))


if __name__ == "__main__":
    main()
