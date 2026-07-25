#!/usr/bin/env python3
"""
Demo seed script for TellUS AI.
Creates a single demo company with employees, departments, and sample requests.

Usage (from backend root):
    uv run python scripts/seed_demo.py

Dependencies:
    - backend environment must be configured (via .env)
    - database connection must be available
"""

import asyncio
import os
from uuid import uuid4, UUID
from datetime import date, datetime, UTC

from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("SECRET_KEY", "demo-secret-key-not-for-production")

from app.database.session import create_database_engine, create_session_factory
from app.companies.repository import CompanyRepository
from app.departments.repository import DepartmentRepository
from app.employees.repository import EmployeeRepository
from app.users.repository import UserRepository
from app.business_requests.repository import BusinessRequestRepository
from app.core.enums import ActorType, RequestStatus, RequestPriority
from app.auth.passwords import hash_password
from app.database import models  # noqa: F401


DEMO_COMPANY_NAME = "Acme Corporation"
DEMO_COMPANY_SLUG = "acme"
DEPARTMENTS = [
    ("Customer Support", "customer_support"),
    ("Human Resources", "hr"),
    ("Information Technology", "it"),
    ("Finance", "finance"),
    ("Procurement", "procurement"),
]

EMPLOYEES = [
    # dept_name, code, job_title, hire_date
    ("Customer Support", "EMP001", "Support Specialist", date(2020, 3, 15)),
    ("Human Resources", "EMP002", "HR Manager", date(2019, 6, 1)),
    ("Information Technology", "EMP003", "IT Administrator", date(2021, 1, 10)),
    ("Finance", "EMP004", "Finance Analyst", date(2020, 8, 22)),
    ("Procurement", "EMP005", "Procurement Officer", date(2021, 5, 5)),
]

REQUESTS = [
    {
        "request_type": "leave_request",
        "title": "Annual Leave Request",
        "summary": "Requesting 5 days of annual leave in August.",
        "status": RequestStatus.COMPLETED,
        "priority": RequestPriority.NORMAL,
        "current_stage": "completed",
    },
    {
        "request_type": "expense_reimbursement",
        "title": "Travel Expense Reimbursement",
        "summary": "Reimbursement for client meeting travel expenses.",
        "status": RequestStatus.PROCESSING,
        "priority": RequestPriority.HIGH,
        "current_stage": "finance_approval",
    },
    {
        "request_type": "software_access",
        "title": "Request Access to Analytics Platform",
        "summary": "Need access to the internal analytics dashboard for Q3 reporting.",
        "status": RequestStatus.CREATED,
        "priority": RequestPriority.NORMAL,
        "current_stage": "created",
    },
    {
        "request_type": "procurement_request",
        "title": "Purchase Office Equipment",
        "summary": "Request to purchase 10 new ergonomic chairs for the floor.",
        "status": RequestStatus.WAITING_FOR_HUMAN_APPROVAL,
        "priority": RequestPriority.NORMAL,
        "current_stage": "manager_approval",
    },
]


def _now():
    return datetime.now(UTC)


async def _get_or_create_company(session: AsyncSession) -> UUID:
    repo = CompanyRepository(session)
    existing = await repo.get_by_slug(DEMO_COMPANY_SLUG)
    if existing:
        print(f"  Company already exists: {existing.name} ({existing.id})")
        return existing.id

    company = await repo.create(
        name=DEMO_COMPANY_NAME,
        slug=DEMO_COMPANY_SLUG,
        is_active=True,
    )
    await session.commit()
    print(f"  Created company: {company.name} ({company.id})")
    return company.id


async def _seed_departments(session: AsyncSession, company_id: UUID) -> dict[str, UUID]:
    dept_repo = DepartmentRepository(session, company_id)
    existing = await dept_repo.list()
    mapping: dict[str, UUID] = {}
    for dept in existing:
        mapping[dept.department_type] = dept.id

    for name, dept_type in DEPARTMENTS:
        if dept_type in mapping:
            print(f"    Department exists: {name}")
            continue
        dept = await dept_repo.create(
            name=name,
            department_type=dept_type,
        )
        mapping[dept_type] = dept.id
        print(f"    Created department: {name}")

    await session.commit()
    return mapping


async def _seed_company_account(session: AsyncSession, company_id: UUID) -> UUID:
    user_repo = UserRepository(session, company_id)
    email = "admin@acme.example"
    existing = await user_repo.get_by_email(email)
    if existing:
        print(f"    Company account exists: {email}")
        return existing.id

    user = await user_repo.create(
        email=email,
        actor_type=ActorType.COMPANY,
        is_active=True,
        password_hash=hash_password("DemoPassword123!"),
    )
    await session.commit()
    print(f"    Created company account: {email}")
    return user.id


async def _seed_employees_and_managers(session: AsyncSession, company_id: UUID, dept_map: dict[str, UUID]) -> list[UUID]:
    emp_repo = EmployeeRepository(session, company_id)
    user_repo = UserRepository(session, company_id)
    existing_emps = await emp_repo.list()
    existing_codes = {e.employee_code for e in existing_emps}

    user_ids: list[UUID] = []
    for dept_type, code, job_title, hire_date in EMPLOYEES:
        if code in existing_codes:
            emp = next((e for e in existing_emps if e.employee_code == code), None)
            if emp:
                user_ids.append(emp.id)
            print(f"    Employee exists: {code}")
            continue

        email = f"{code.lower()}@acme.example"
        user = await user_repo.create(
            email=email,
            actor_type=ActorType.EMPLOYEE,
            is_active=True,
            password_hash=hash_password("DemoPassword123!"),
        )
        dept_id = dept_map.get(dept_type)
        emp = await emp_repo.create(
            employee_code=code,
            job_title=job_title,
            department_id=dept_id,
            user_id=user.id,
            hire_date=hire_date,
        )
        user_ids.append(emp.id)
        print(f"    Created employee: {code} ({email})")

    await session.commit()
    return user_ids


async def _seed_requests(session: AsyncSession, company_id: UUID, requester_user_id: UUID) -> None:
    req_repo = BusinessRequestRepository(session, company_id)
    existing = await req_repo.list()
    existing_titles = {r.title for r in existing}

    for payload in REQUESTS:
        if payload["title"] in existing_titles:
            print(f"    Request exists: {payload['title']}")
            continue

        req = await req_repo.create(
            request_type=payload["request_type"],
            title=payload["title"],
            summary=payload["summary"],
            priority=payload["priority"],
            requester_user_id=requester_user_id,
            requester_employee_id=None,
        )
        # Set explicit status for demo variety
        req.status = payload["status"]
        req.current_stage = payload["current_stage"]
        if payload["status"] == RequestStatus.COMPLETED:
            req.final_decision = "Approved"
            req.completed_at = _now()
        await session.flush()
        print(f"    Created request: {payload['title']} ({payload['status'].value})")

    await session.commit()


async def seed() -> None:
    engine = create_database_engine()
    factory = create_session_factory(engine)
    async with factory() as session:
        print("\n⚙️  Seeding demo data...")
        company_id = await _get_or_create_company(session)
        dept_map = await _seed_departments(session, company_id)
        await _seed_company_account(session, company_id)
        emp_ids = await _seed_employees_and_managers(session, company_id, dept_map)
        # Seed sample requests — use first employee's identity if available, else company account
        if emp_ids:
            requester = await UserRepository(session, company_id).get_by_id(emp_ids[0])
            requester_id = requester.id if requester else None
        else:
            requester_id = None
        if requester_id:
            await _seed_requests(session, company_id, requester_id)
        print("\n✅ Demo seed complete.\n")


if __name__ == "__main__":
    asyncio.run(seed())
