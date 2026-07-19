from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.enums import ActorType, DepartmentType
from app.database.session import get_db_session
from app.departments.procurement.repository import (
    ProcurementRequestRepository,
    SupplierCandidateRepository,
)
from app.departments.procurement.schemas import (
    ProcurementRequestResponse,
    SupplierCandidateCreate,
    SupplierCandidateResponse,
    SupplierCandidateUpdate,
)
from app.departments.procurement.service import ProcurementService
from app.departments.repository import DepartmentRepository


router = APIRouter(tags=["procurement"])


async def _procurement_manager(
    session: AsyncSession, current_user: AuthenticatedUser
) -> bool:
    if (
        current_user.actor_type != ActorType.DEPARTMENT_MANAGER
        or not current_user.is_manager
        or current_user.department_id is None
    ):
        return False
    department = await DepartmentRepository(session, current_user.company_id).get_by_id(
        current_user.department_id
    )
    return bool(
        department is not None
        and department.is_active
        and department.department_type == DepartmentType.PROCUREMENT
    )


async def _can_manage(
    session: AsyncSession, current_user: AuthenticatedUser
) -> bool:
    return current_user.actor_type == ActorType.COMPANY or await _procurement_manager(
        session, current_user
    )


async def _request_or_404(
    session: AsyncSession, current_user: AuthenticatedUser, request_id: UUID
):
    record = await ProcurementRequestRepository(
        session, current_user.company_id
    ).get(request_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )
    broad = await _can_manage(session, current_user)
    collaborating_manager = bool(
        current_user.actor_type == ActorType.DEPARTMENT_MANAGER
        and current_user.is_manager
        and current_user.department_id is not None
        and current_user.department_id == record.requesting_department_id
    )
    if not broad and not collaborating_manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )
    return record


@router.get(
    "/api/v1/procurement-requests/{request_id}",
    response_model=ProcurementRequestResponse,
)
async def get_procurement_request(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> ProcurementRequestResponse:
    record = await _request_or_404(session, current_user, request_id)
    return ProcurementRequestResponse.model_validate(record)


@router.get(
    "/api/v1/procurement-requests/{request_id}/candidates",
    response_model=list[SupplierCandidateResponse],
)
async def list_supplier_candidates(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[SupplierCandidateResponse]:
    await _request_or_404(session, current_user, request_id)
    records = await SupplierCandidateRepository(
        session, current_user.company_id
    ).list_for_request(request_id)
    return [SupplierCandidateResponse.model_validate(item) for item in records]


@router.get(
    "/api/v1/supplier-candidates/{candidate_id}",
    response_model=SupplierCandidateResponse,
)
async def get_supplier_candidate(
    candidate_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> SupplierCandidateResponse:
    candidate = await SupplierCandidateRepository(
        session, current_user.company_id
    ).get(candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier candidate not found",
        )
    await _request_or_404(session, current_user, candidate.request_id)
    return SupplierCandidateResponse.model_validate(candidate)


@router.post(
    "/api/v1/procurement-requests/{request_id}/candidates",
    response_model=SupplierCandidateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier_candidate(
    request_id: UUID,
    payload: SupplierCandidateCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> SupplierCandidateResponse:
    if not await _can_manage(session, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    record = await ProcurementService.create_managed_candidate(
        session, current_user.company_id, request_id, payload
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procurement request not found",
        )
    return SupplierCandidateResponse.model_validate(record)


@router.patch(
    "/api/v1/supplier-candidates/{candidate_id}",
    response_model=SupplierCandidateResponse,
)
async def update_supplier_candidate(
    candidate_id: UUID,
    payload: SupplierCandidateUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> SupplierCandidateResponse:
    if not await _can_manage(session, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    record, selected = await ProcurementService.update_managed_candidate(
        session, current_user.company_id, candidate_id, payload
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Supplier candidate not found",
        )
    if selected:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A selected candidate cannot be changed",
        )
    return SupplierCandidateResponse.model_validate(record)
