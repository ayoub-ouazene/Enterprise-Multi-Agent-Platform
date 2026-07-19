import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.departments.hr.repository import LeaveBalanceRepository


def test_leave_balance_query_is_tenant_scoped() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.scalars.return_value = result
    company_id, employee_id = uuid4(), uuid4()
    asyncio.run(LeaveBalanceRepository(session, company_id).list_for_employee(employee_id))
    statement = session.scalars.await_args.args[0]
    rendered = str(statement)
    assert "leave_balances.company_id" in rendered
    assert "leave_balances.employee_id" in rendered
