from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.departments.contracts import DepartmentToolRequest
from app.departments.hr.calculations import calculate_workdays
from app.departments.hr.enums import LeaveDecision, LeaveType
from app.departments.hr.repository import (
    CompanyHolidayRepository,
    JobDescriptionRepository,
    LeaveBalanceRepository,
    LeaveRequestRepository,
    OnboardingRequestRepository,
)


class HROperationError(RuntimeError):
    pass


class LeaveArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: UUID
    leave_type: LeaveType
    year: int


class CalculateArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date


class HRToolService:
    """Allowlisted deterministic HR tools; the caller controls transactions."""

    def __init__(self, balances: LeaveBalanceRepository, leave_requests: LeaveRequestRepository,
                 holidays: CompanyHolidayRepository, onboarding: OnboardingRequestRepository,
                 job_descriptions: JobDescriptionRepository, *, request_id: UUID) -> None:
        self.balances, self.leave_requests, self.holidays = balances, leave_requests, holidays
        self.onboarding, self.job_descriptions, self.request_id = onboarding, job_descriptions, request_id

    async def execute(self, request: DepartmentToolRequest) -> dict[str, Any]:
        if request.operation == "get_leave_balance":
            args = LeaveArguments.model_validate(request.arguments)
            record = await self.balances.get_for_employee(args.employee_id, args.leave_type, args.year)
            if record is None:
                return {"operation": request.operation, "found": False}
            return {"operation": request.operation, "found": True, "allocated_days": str(record.allocated_days),
                    "used_days": str(record.used_days), "reserved_days": str(record.reserved_days),
                    "remaining_days": str(record.remaining_days)}
        if request.operation == "calculate_leave_days":
            args = CalculateArguments.model_validate(request.arguments)
            holidays = await self.holidays.dates_between(args.start_date, args.end_date)
            return {"operation": request.operation, "requested_days": str(calculate_workdays(args.start_date, args.end_date, holidays))}
        if request.operation == "get_onboarding_status":
            record = await self.onboarding.get(self.request_id)
            return {"operation": request.operation, "found": record is not None,
                    "status": record.onboarding_status.value if record else None}
        if request.operation in {"check_leave_eligibility", "check_minimum_staffing",
                                 "reserve_leave_days", "release_leave_days",
                                 "finalize_leave_usage", "create_job_description_draft"}:
            raise HROperationError("This HR operation is executed only by the authoritative HR service")
        raise HROperationError("HR tool operation is not allowlisted")


async def release_leave_reservation(
    balances: LeaveBalanceRepository,
    leave_requests: LeaveRequestRepository,
    request_id: UUID,
) -> bool:
    leave = await leave_requests.get(request_id, for_update=True)
    if leave is None or leave.reserved_days <= 0:
        return False
    balance = await balances.get_for_employee(leave.employee_id, leave.leave_type, leave.start_date.year, for_update=True)
    if balance is None:
        raise HROperationError("Leave balance is unavailable")
    amount = leave.reserved_days
    if balance.reserved_days < amount:
        raise HROperationError("Leave reservation state is inconsistent")
    balance.reserved_days -= amount
    leave.reserved_days = Decimal("0.00")
    if leave.decision != LeaveDecision.REJECTED:
        leave.decision = LeaveDecision.CANCELLED
    await balances.session.flush()
    return True
