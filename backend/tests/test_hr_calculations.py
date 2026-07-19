from datetime import date
from decimal import Decimal

import pytest

from app.departments.hr.calculations import (
    HRBusinessDecisionError,
    calculate_workdays,
    remaining_days,
    staffing_satisfied,
)


def test_workdays_exclude_weekends_and_company_holidays() -> None:
    assert calculate_workdays(date(2026, 7, 17), date(2026, 7, 22), {date(2026, 7, 20)}) == Decimal("3.00")


def test_invalid_date_range_is_rejected() -> None:
    with pytest.raises(HRBusinessDecisionError, match="before"):
        calculate_workdays(date(2026, 7, 20), date(2026, 7, 19))


def test_exact_balance_math_and_negative_prevention() -> None:
    assert remaining_days(Decimal("20.00"), Decimal("3.00"), Decimal("2.00")) == Decimal("15.00")
    with pytest.raises(HRBusinessDecisionError):
        remaining_days(Decimal("3.00"), Decimal("2.00"), Decimal("2.00"))


def test_staffing_is_deterministic() -> None:
    assert staffing_satisfied(active_employees=5, overlapping_absences=1, minimum_active=3)
    assert not staffing_satisfied(active_employees=4, overlapping_absences=1, minimum_active=3)
