import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.procurement.agent import ProcurementDepartmentAgent


def execution_context(active=DepartmentType.PROCUREMENT):
    return DepartmentExecutionContext(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        owner_department_type=DepartmentType.PROCUREMENT,
        active_department_type=active, request_type="supplier_evaluation",
        request_summary="Evaluate laptop suppliers", current_stage="processing",
    )


def test_procurement_agent_delegates_to_service() -> None:
    service = AsyncMock()
    service.execute.return_value = {"ok": True}
    result = asyncio.run(ProcurementDepartmentAgent(service).execute(execution_context()))
    assert result == {"ok": True}
    service.execute.assert_awaited_once()


def test_procurement_agent_rejects_wrong_active_department() -> None:
    with pytest.raises(DepartmentContextMismatchError):
        asyncio.run(
            ProcurementDepartmentAgent(AsyncMock()).execute(
                execution_context(DepartmentType.IT)
            )
        )
