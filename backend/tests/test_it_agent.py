import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4
from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.it.agent import ITDepartmentAgent


def test_real_it_agent_delegates_trusted_context() -> None:
    service = AsyncMock()
    service.execute.return_value = object()
    context = DepartmentExecutionContext(request_id=uuid4(), company_id=uuid4(),
        requester_user_id=uuid4(), requester_actor_type="employee",
        owner_department_type=DepartmentType.IT, active_department_type=DepartmentType.IT,
        request_type="software_access", request_summary="Need editor access", current_stage="it_analysis")
    assert asyncio.run(ITDepartmentAgent(service).execute(context)) is service.execute.return_value
    service.execute.assert_awaited_once_with(context)
