from datetime import date, timedelta
from decimal import Decimal


class HRBusinessDecisionError(ValueError):
    """A safe HR business outcome, not a technical execution failure."""


def calculate_workdays(
    start_date: date,
    end_date: date,
    holidays: set[date] | frozenset[date] = frozenset(),
) -> Decimal:
    if end_date < start_date:
        raise HRBusinessDecisionError("Leave end date cannot be before start date")
    current = start_date
    count = 0
    while current <= end_date:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    if count == 0:
        raise HRBusinessDecisionError("The selected range contains no working days")
    return Decimal(count).quantize(Decimal("0.01"))


def remaining_days(allocated: Decimal, used: Decimal, reserved: Decimal) -> Decimal:
    result = allocated - used - reserved
    if min(allocated, used, reserved, result) < 0:
        raise HRBusinessDecisionError("Leave balance is invalid or insufficient")
    return result.quantize(Decimal("0.01"))


def staffing_satisfied(
    *, active_employees: int, overlapping_absences: int, minimum_active: int
) -> bool:
    if min(active_employees, overlapping_absences, minimum_active) < 0:
        raise HRBusinessDecisionError("Staffing values cannot be negative")
    return active_employees - overlapping_absences - 1 >= minimum_active
