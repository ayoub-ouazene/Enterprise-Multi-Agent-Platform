import asyncio
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.core.enums import EmploymentStatus
from app.departments.contracts import DepartmentExecutionContext, DepartmentNextAction
from app.departments.hr.enums import HRDecision, LeaveDecision
from app.departments.hr.schemas import HRDepartmentResult, HRStateUpdates
from app.departments.hr.service import HRService


def test_leave_balance_remaining_is_exact_decimal() -> None:
    from app.departments.hr.calculations import remaining_days
    assert remaining_days(Decimal("10.00"), Decimal("2.00"), Decimal("1.00")) == Decimal("7.00")


def test_approved_leave_reservation_is_request_owned() -> None:
    record = SimpleNamespace(decision=LeaveDecision.APPROVED, requested_days=Decimal("2.00"), reserved_days=Decimal("2.00"))
    assert record.reserved_days == record.requested_days


def leave_result() -> HRDepartmentResult:
    return HRDepartmentResult(
        category="leave_request", decision="eligible", reason="Initial interpretation",
        user_message="Initial interpretation", confidence="high", leave_eligible=True,
        leave_balance_sufficient=True, minimum_staffing_satisfied=True,
        next_action="complete_request", safe_event_title="Leave checked",
        safe_event_message="Leave was checked.",
        state_updates=HRStateUpdates(employee_id=EMPLOYEE_ID, leave_type="annual",
            start_date=date(2026, 7, 20), end_date=date(2026, 7, 21)),
    )


EMPLOYEE_ID = uuid4()
DEPARTMENT_ID = uuid4()


def service(auto: bool, remaining: Decimal = Decimal("10.00")) -> HRService:
    value = HRService.__new__(HRService)
    value.employees = AsyncMock()
    value.employees.get_by_id.return_value = SimpleNamespace(
        id=EMPLOYEE_ID, employment_status=EmploymentStatus.ACTIVE,
        department_id=DEPARTMENT_ID,
    )
    value.employees.active_ids_in_department.return_value = [uuid4() for _ in range(5)]
    value.holidays = AsyncMock()
    value.holidays.dates_between.return_value = set()
    value.balances = AsyncMock()
    value.balances.get_for_employee.return_value = SimpleNamespace(
        remaining_days=remaining,
        custom_data={"auto_approval_enabled": auto, "auto_approval_max_days": "5"},
    )
    value.staffing = AsyncMock()
    value.staffing.applicable.return_value = SimpleNamespace(minimum_active_employees=3)
    value.leave_requests = AsyncMock()
    value.leave_requests.overlapping_count.return_value = 0
    return value


def context() -> DepartmentExecutionContext:
    return DepartmentExecutionContext(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        requester_employee_id=EMPLOYEE_ID, requester_department_id=DEPARTMENT_ID,
        requester_actor_type="employee", owner_department_type="hr",
        active_department_type="hr", request_type="leave_request",
        request_summary="Annual leave", current_stage="hr_analysis",
    )


def test_automatic_approval_uses_authoritative_checks() -> None:
    result = asyncio.run(service(True)._apply_authoritative_facts(leave_result(), context()))
    assert result.decision == HRDecision.APPROVED
    assert result.next_action == DepartmentNextAction.COMPLETE_REQUEST
    assert result.state_updates.requested_days == Decimal("2.00")


def test_manager_approval_path_does_not_reserve_early() -> None:
    result = asyncio.run(service(False)._apply_authoritative_facts(leave_result(), context()))
    assert result.decision == HRDecision.PENDING_APPROVAL
    assert result.next_action == DepartmentNextAction.REQUEST_HUMAN_ACTION
    assert result.state_updates.reserved_days == Decimal("0.00")
    assert result.human_action_request is not None


def test_insufficient_balance_is_safe_rejection() -> None:
    result = asyncio.run(service(True, Decimal("1.00"))._apply_authoritative_facts(leave_result(), context()))
    assert result.decision == HRDecision.REJECTED
    assert result.next_action == DepartmentNextAction.COMPLETE_REQUEST
