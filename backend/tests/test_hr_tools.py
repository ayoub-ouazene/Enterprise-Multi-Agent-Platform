import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.departments.contracts import DepartmentToolRequest
from app.departments.hr.tools import HRToolService
from app.departments.hr.tools import release_leave_reservation


def test_calculate_leave_days_uses_company_holidays() -> None:
    balances, leaves, holidays, onboarding, jobs = (AsyncMock() for _ in range(5))
    holidays.dates_between.return_value = {date(2026, 7, 20)}
    tool = HRToolService(balances, leaves, holidays, onboarding, jobs, request_id=uuid4())
    request = DepartmentToolRequest(tool_name="hr", operation="calculate_leave_days",
        arguments={"start_date": "2026-07-17", "end_date": "2026-07-21"}, reason="Calculate", expected_result_type="leave_days")
    result = asyncio.run(tool.execute(request))
    assert result["requested_days"] == "2.00"


def test_release_leave_reservation_is_idempotent() -> None:
    balances, leaves = AsyncMock(), AsyncMock()
    leave = SimpleNamespace(employee_id=uuid4(), leave_type="annual", start_date=date(2026, 1, 1),
        reserved_days=Decimal("2.00"), decision="approved")
    balance = SimpleNamespace(reserved_days=Decimal("2.00"))
    leaves.get.return_value = leave
    balances.get_for_employee.return_value = balance
    assert asyncio.run(release_leave_reservation(balances, leaves, uuid4()))
    assert leave.reserved_days == Decimal("0.00")
    assert not asyncio.run(release_leave_reservation(balances, leaves, uuid4()))
