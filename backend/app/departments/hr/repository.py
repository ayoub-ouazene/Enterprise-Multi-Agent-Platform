from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.departments.hr.enums import LeaveDecision, LeaveType
from app.departments.hr.models import (
    CompanyHoliday,
    DepartmentStaffingRule,
    JobDescription,
    LeaveBalance,
    LeaveRequest,
    OnboardingRequest,
)


class TenantRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id


class LeaveBalanceRepository(TenantRepository):
    async def get(self, balance_id: UUID, *, for_update: bool = False) -> LeaveBalance | None:
        statement = select(LeaveBalance).where(LeaveBalance.id == balance_id, LeaveBalance.company_id == self.company_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def get_for_employee(self, employee_id: UUID, leave_type: LeaveType, year: int, *, for_update: bool = False) -> LeaveBalance | None:
        statement = select(LeaveBalance).where(
            LeaveBalance.company_id == self.company_id, LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type, LeaveBalance.year == year,
        )
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list_for_employee(self, employee_id: UUID) -> list[LeaveBalance]:
        records = await self.session.scalars(select(LeaveBalance).where(
            LeaveBalance.company_id == self.company_id, LeaveBalance.employee_id == employee_id
        ).order_by(LeaveBalance.year.desc(), LeaveBalance.leave_type))
        return list(records.all())


class LeaveRequestRepository(TenantRepository):
    async def get(self, request_id: UUID, *, for_update: bool = False) -> LeaveRequest | None:
        statement = select(LeaveRequest).where(LeaveRequest.request_id == request_id, LeaveRequest.company_id == self.company_id)
        if for_update:
            statement = statement.with_for_update()
        record = await self.session.scalar(statement)
        return record if isinstance(record, LeaveRequest) else None

    async def list_for_employee(self, employee_id: UUID) -> list[LeaveRequest]:
        records = await self.session.scalars(select(LeaveRequest).where(
            LeaveRequest.company_id == self.company_id, LeaveRequest.employee_id == employee_id
        ).order_by(LeaveRequest.created_at.desc()))
        return list(records.all())

    async def overlapping_count(self, department_employee_ids: list[UUID], start_date: date, end_date: date, *, exclude_request_id: UUID | None = None) -> int:
        if not department_employee_ids:
            return 0
        conditions = [
            LeaveRequest.company_id == self.company_id,
            LeaveRequest.employee_id.in_(department_employee_ids),
            LeaveRequest.decision == LeaveDecision.APPROVED,
            LeaveRequest.reserved_days > 0,
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        ]
        if exclude_request_id is not None:
            conditions.append(LeaveRequest.request_id != exclude_request_id)
        result = await self.session.scalars(select(LeaveRequest.employee_id).where(*conditions).distinct())
        return len(result.all())

    async def upsert(self, request_id: UUID, values: dict[str, object]) -> LeaveRequest:
        record = await self.get(request_id, for_update=True)
        if record is None:
            record = LeaveRequest(request_id=request_id, company_id=self.company_id, **values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record


class CompanyHolidayRepository(TenantRepository):
    async def dates_between(self, start_date: date, end_date: date) -> set[date]:
        values = await self.session.scalars(select(CompanyHoliday.holiday_date).where(
            CompanyHoliday.company_id == self.company_id,
            CompanyHoliday.holiday_date.between(start_date, end_date),
        ))
        return set(values.all())


class DepartmentStaffingRuleRepository(TenantRepository):
    async def applicable(self, department_id: UUID, start_date: date, end_date: date, *, for_update: bool = False) -> DepartmentStaffingRule | None:
        statement = select(DepartmentStaffingRule).where(
            DepartmentStaffingRule.company_id == self.company_id,
            DepartmentStaffingRule.department_id == department_id,
            DepartmentStaffingRule.is_active.is_(True),
            DepartmentStaffingRule.effective_from <= start_date,
            or_(DepartmentStaffingRule.effective_to.is_(None), DepartmentStaffingRule.effective_to >= end_date),
        ).order_by(DepartmentStaffingRule.effective_from.desc()).limit(1)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)


class OnboardingRequestRepository(TenantRepository):
    async def get(self, request_id: UUID, *, for_update: bool = False) -> OnboardingRequest | None:
        statement = select(OnboardingRequest).where(OnboardingRequest.request_id == request_id, OnboardingRequest.company_id == self.company_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert(self, request_id: UUID, values: dict[str, object]) -> OnboardingRequest:
        record = await self.get(request_id, for_update=True)
        if record is None:
            record = OnboardingRequest(request_id=request_id, company_id=self.company_id, **values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record


class JobDescriptionRepository(TenantRepository):
    async def get(self, record_id: UUID) -> JobDescription | None:
        return await self.session.scalar(select(JobDescription).where(JobDescription.id == record_id, JobDescription.company_id == self.company_id))

    async def get_for_request(self, request_id: UUID, *, for_update: bool = False) -> JobDescription | None:
        statement = select(JobDescription).where(JobDescription.request_id == request_id, JobDescription.company_id == self.company_id)
        if for_update:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def upsert_for_request(self, request_id: UUID, values: dict[str, object]) -> JobDescription:
        record = await self.get_for_request(request_id, for_update=True)
        if record is None:
            record = JobDescription(request_id=request_id, company_id=self.company_id, **values)
            self.session.add(record)
        else:
            for key, value in values.items():
                setattr(record, key, value)
        await self.session.flush()
        return record
