from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.enums import ActorType, DepartmentType
from app.database.session import get_db_session
from app.departments.hr.repository import (
    JobDescriptionRepository,
    LeaveBalanceRepository,
    LeaveRequestRepository,
    OnboardingRequestRepository,
)
from app.departments.hr.schemas import (
    JobDescriptionResponse,
    LeaveBalanceResponse,
    LeaveRequestResponse,
    OnboardingRequestResponse,
)
from app.departments.repository import DepartmentRepository
from app.employees.repository import EmployeeRepository


router = APIRouter(tags=["hr"])


async def _is_hr_manager(session: AsyncSession, user: AuthenticatedUser) -> bool:
    if user.actor_type != ActorType.DEPARTMENT_MANAGER or not user.is_manager or user.department_id is None:
        return False
    department = await DepartmentRepository(session, user.company_id).get_by_id(user.department_id)
    return bool(department and department.is_active and department.department_type == DepartmentType.HR)


async def _broad_hr_access(session: AsyncSession, user: AuthenticatedUser) -> bool:
    return user.actor_type == ActorType.COMPANY or await _is_hr_manager(session, user)


async def _can_view_employee(session: AsyncSession, user: AuthenticatedUser, employee_id: UUID) -> bool:
    if await _broad_hr_access(session, user):
        return True
    if user.employee_id == employee_id:
        return True
    if user.actor_type == ActorType.DEPARTMENT_MANAGER and user.is_manager and user.employee_id:
        employee = await EmployeeRepository(session, user.company_id).get_by_id(employee_id)
        return bool(employee and employee.manager_employee_id == user.employee_id)
    return False


@router.get("/api/v1/leave-balances/me", response_model=list[LeaveBalanceResponse])
async def my_leave_balances(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[LeaveBalanceResponse]:
    if user.employee_id is None or user.actor_type == ActorType.EXTERNAL_USER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee access required")
    records = await LeaveBalanceRepository(session, user.company_id).list_for_employee(user.employee_id)
    return [LeaveBalanceResponse.model_validate(item) for item in records]


@router.get("/api/v1/leave-requests/me", response_model=list[LeaveRequestResponse])
async def my_leave_requests(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[LeaveRequestResponse]:
    if user.employee_id is None or user.actor_type == ActorType.EXTERNAL_USER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employee access required")
    records = await LeaveRequestRepository(session, user.company_id).list_for_employee(user.employee_id)
    return [LeaveRequestResponse.model_validate(item) for item in records]


@router.get("/api/v1/leave-requests/{request_id}", response_model=LeaveRequestResponse)
async def get_leave_request(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> LeaveRequestResponse:
    record = await LeaveRequestRepository(session, user.company_id).get(request_id)
    if record is None or not await _can_view_employee(session, user, record.employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    return LeaveRequestResponse.model_validate(record)


@router.get("/api/v1/onboarding-requests/{request_id}", response_model=OnboardingRequestResponse)
async def get_onboarding_request(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> OnboardingRequestResponse:
    record = await OnboardingRequestRepository(session, user.company_id).get(request_id)
    if record is None or not await _can_view_employee(session, user, record.employee_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding request not found")
    return OnboardingRequestResponse.model_validate(record)


@router.get("/api/v1/job-descriptions/{job_description_id}", response_model=JobDescriptionResponse)
async def get_job_description(
    job_description_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> JobDescriptionResponse:
    record = await JobDescriptionRepository(session, user.company_id).get(job_description_id)
    if record is None or not (await _broad_hr_access(session, user) or record.created_by_user_id == user.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job description not found")
    return JobDescriptionResponse.model_validate(record)
