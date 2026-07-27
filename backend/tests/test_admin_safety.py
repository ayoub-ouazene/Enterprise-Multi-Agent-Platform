from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.admin.schemas import (
    AdminAssetCreate,
    AdminDepartmentUpdate,
    AdminEmployeeUpdate,
    AdminHolidayCreate,
)
from app.admin.service import (
    AdminAssetService,
    AdminDepartmentService,
    AdminEmployeeService,
    AdminHolidayService,
)
from app.core.enums import ActorType, EmploymentStatus
from app.core.exceptions import BusinessValidationError, ConflictError
from app.departments.it.enums import AssetStatus


@pytest.mark.asyncio
async def test_department_disable_is_blocked_while_active_members_remain() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
    service = AdminDepartmentService(session, uuid4())
    service.repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(id=uuid4())),
        update=AsyncMock(),
    )

    with pytest.raises(ConflictError, match="active department members"):
        await service.update(
            service.repo.get_by_id.return_value.id,
            AdminDepartmentUpdate(is_active=False),
        )
    service.repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_department_manager_employee_cannot_be_deactivated_directly() -> None:
    service = AdminEmployeeService(AsyncMock(), uuid4())
    service.repo = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                user=SimpleNamespace(actor_type=ActorType.DEPARTMENT_MANAGER),
                user_id=uuid4(),
            )
        )
    )

    with pytest.raises(ConflictError, match="replacement department manager"):
        await service.soft_delete(uuid4())


@pytest.mark.asyncio
async def test_employee_cannot_bypass_deactivation_blockers_with_update() -> None:
    employee_id = uuid4()
    service = AdminEmployeeService(AsyncMock(), uuid4())
    service.repo = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                id=employee_id,
                employment_status=EmploymentStatus.ACTIVE,
            )
        )
    )

    with pytest.raises(BusinessValidationError, match="deactivation operation"):
        await service.update(
            employee_id,
            AdminEmployeeUpdate(employment_status=EmploymentStatus.TERMINATED),
        )


@pytest.mark.asyncio
async def test_asset_assignment_requires_active_company_employee() -> None:
    service = AdminAssetService(AsyncMock(), uuid4())
    service.repo = SimpleNamespace(create=AsyncMock())
    employee_id = uuid4()
    service.session.scalar = AsyncMock()

    from app.admin.repository import EmployeeAdminRepository

    original = EmployeeAdminRepository.get
    try:
        EmployeeAdminRepository.get = AsyncMock(  # type: ignore[method-assign]
            return_value=SimpleNamespace(
                id=employee_id,
                employment_status=EmploymentStatus.TERMINATED,
            )
        )
        with pytest.raises(BusinessValidationError, match="active company employees"):
            await service.create(
                AdminAssetCreate(
                    asset_code="ASSET-1",
                    asset_type="laptop",
                    brand="Example",
                    model="Secure",
                    assigned_employee_id=employee_id,
                    status=AssetStatus.ASSIGNED,
                )
            )
    finally:
        EmployeeAdminRepository.get = original  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_duplicate_holiday_date_is_a_conflict() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=uuid4())
    service = AdminHolidayService(session, uuid4())
    service.repo = SimpleNamespace(create=AsyncMock())

    with pytest.raises(ConflictError, match="already exists"):
        await service.create(
            AdminHolidayCreate(
                holiday_date=date(2026, 1, 1),
                name="New year",
            )
        )
    service.repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_reporting_manager_does_not_grant_department_manager_role() -> None:
    employee_id = uuid4()
    manager_id = uuid4()
    manager = SimpleNamespace(
        id=manager_id,
        user_id=uuid4(),
        employment_status=EmploymentStatus.ACTIVE,
        manager_employee_id=None,
    )
    employee = SimpleNamespace(
        id=employee_id,
        user_id=uuid4(),
        employment_status=EmploymentStatus.ACTIVE,
    )
    refreshed = SimpleNamespace(**employee.__dict__, user=None)
    service = AdminEmployeeService(AsyncMock(), uuid4())
    service.repo = SimpleNamespace(
        get=AsyncMock(side_effect=[employee, manager, refreshed]),
        update=AsyncMock(return_value=employee),
        get_by_email=AsyncMock(return_value=None),
    )

    await service.update(
        employee_id,
        AdminEmployeeUpdate(manager_employee_id=manager_id),
    )

    service.session.execute.assert_not_awaited()
