import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.hr.agent import HRDepartmentAgent
from app.departments.registry import build_default_department_registry


def test_registry_resolves_real_hr_and_all_five_departments() -> None:
    registry = build_default_department_registry(hr_agent=HRDepartmentAgent(AsyncMock()))
    assert isinstance(registry.resolve(DepartmentType.HR), HRDepartmentAgent)
    assert set(registry.registered_types) == set(DepartmentType)


def test_hr_agent_delegates_to_service() -> None:
    service = AsyncMock()
    expected = object()
    service.execute.return_value = expected
    context = DepartmentExecutionContext(request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        owner_department_type="hr", active_department_type="hr", request_type="leave_request",
        request_summary="Leave", current_stage="hr")
    assert asyncio.run(HRDepartmentAgent(service).execute(context)) is expected
