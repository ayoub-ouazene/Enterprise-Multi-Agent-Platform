import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.finance.agent import FinanceDepartmentAgent


def context(active: DepartmentType = DepartmentType.FINANCE) -> DepartmentExecutionContext:
    return DepartmentExecutionContext(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        owner_department_type=DepartmentType.FINANCE, active_department_type=active,
        request_type="budget_inquiry", request_summary="Show the budget status",
        current_stage="finance_analysis",
    )


def test_real_finance_agent_delegates_trusted_context() -> None:
    service = AsyncMock()
    service.execute.return_value = object()
    result = asyncio.run(FinanceDepartmentAgent(service).execute(context()))
    assert result is service.execute.return_value
    service.execute.assert_awaited_once()


def test_finance_agent_rejects_wrong_active_department() -> None:
    with pytest.raises(DepartmentContextMismatchError):
        asyncio.run(FinanceDepartmentAgent(AsyncMock()).execute(context(DepartmentType.IT)))
