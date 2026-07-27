from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.enums import ActorType, DepartmentType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.departments.repository import DepartmentRepository
from app.departments.schemas import (
    DepartmentActivityResponse,
    DepartmentOperationalRecordResponse,
    DepartmentReadinessResponse,
    DepartmentResponse,
    DepartmentStatsResponse,
)
from app.departments.service import DepartmentWorkspaceService
from app.requests.permissions import can_view_business_request
from app.requests.schemas import BusinessRequestSummaryResponse
from app.requests.service import BusinessRequestService
from app.human_actions.schemas import HumanActionResponse

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])


async def _resolve_department(
    dept_type: DepartmentType,
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> UUID:
    """Resolve department_type to department_id for the tenant."""
    department = await DepartmentRepository(
        session, current_user.company_id
    ).get_by_type(dept_type)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    return department.id


async def _require_department_access(
    dept_type: DepartmentType,
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> UUID:
    """Require company-wide or matching active department access."""
    department = await DepartmentRepository(
        session, current_user.company_id
    ).get_by_type(dept_type)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    dept_id = department.id
    if current_user.actor_type == ActorType.COMPANY:
        return dept_id
    if (
        current_user.actor_type in {
            ActorType.DEPARTMENT_MANAGER,
            ActorType.EMPLOYEE,
        }
        and current_user.department_id == dept_id
        and department.is_active
    ):
        return dept_id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[DepartmentResponse]:
    if current_user.actor_type == ActorType.EXTERNAL_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department workspace access is not available",
        )
    records = await DepartmentRepository(
        session, current_user.company_id
    ).list()
    if current_user.actor_type != ActorType.COMPANY:
        records = [
            record
            for record in records
            if record.id == current_user.department_id and record.is_active
        ]
    return [DepartmentResponse.model_validate(item) for item in records]


@router.get("/{dept_type}/stats", response_model=DepartmentStatsResponse)
async def get_department_stats(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> DepartmentStatsResponse:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    return await service.get_stats(dept_id, current_user=current_user)


@router.get("/{dept_type}/requests", response_model=list[BusinessRequestSummaryResponse])
async def list_department_requests(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BusinessRequestSummaryResponse]:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    records = await service.list_requests(
        dept_id, status_filter=status_filter, limit=limit, offset=offset
    )
    # Visibility filter: managers/company can see all dept requests; others only their own
    visible = [
        r for r in records
        if can_view_business_request(current_user, r)
    ]
    return await BusinessRequestService(session, current_user).present_summaries(visible)


@router.get("/{dept_type}/actions", response_model=list[HumanActionResponse])
async def list_department_actions(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[HumanActionResponse]:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    return await service.list_actions(
        dept_id,
        current_user=current_user,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/{dept_type}/readiness", response_model=DepartmentReadinessResponse)
async def get_department_readiness(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> DepartmentReadinessResponse:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    return await service.get_readiness(dept_id, dept_type)


@router.get("/{dept_type}/activity", response_model=list[DepartmentActivityResponse])
async def get_department_activity(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DepartmentActivityResponse]:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    return await service.get_activity(
        dept_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{dept_type}/operational-records",
    response_model=list[DepartmentOperationalRecordResponse],
)
async def list_department_operational_records(
    dept_type: DepartmentType,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    kind: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> list[DepartmentOperationalRecordResponse]:
    dept_id = await _require_department_access(dept_type, session, current_user)
    service = DepartmentWorkspaceService(session, current_user.company_id)
    return await service.list_operational_records(
        dept_id,
        dept_type,
        current_user=current_user,
        kind=kind,
        limit=limit,
    )
