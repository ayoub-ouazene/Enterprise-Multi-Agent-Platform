import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.customer_support.agent import CustomerSupportDepartmentAgent


def test_agent_delegates_only_matching_customer_support_context() -> None:
    service = AsyncMock()
    service.execute.return_value = object()
    context = DepartmentExecutionContext(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        owner_department_type=DepartmentType.CUSTOMER_SUPPORT,
        active_department_type=DepartmentType.CUSTOMER_SUPPORT,
        request_type="support_question", request_summary="How do I sign in?",
        current_stage="customer_support_analysis",
    )
    result = asyncio.run(CustomerSupportDepartmentAgent(service).execute(context))
    assert result is service.execute.return_value
    service.execute.assert_awaited_once_with(context)
