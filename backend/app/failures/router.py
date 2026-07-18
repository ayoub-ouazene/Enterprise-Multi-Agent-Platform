from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_actor_type, require_company_account
from app.core.enums import ActorType
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.failures.schemas import (
    CapabilityGapDetailResponse,
    CapabilityGapListFilters,
    CapabilityGapStatusUpdate,
    CapabilityGapSummaryResponse,
    FailureDetailResponse,
    FailureListFilters,
)
from app.failures.service import (
    CapabilityGapService,
    FailurePermissionError,
    FailureService,
)


router = APIRouter(tags=["failure-management"])
management_dependency = require_actor_type(
    ActorType.COMPANY, ActorType.DEPARTMENT_MANAGER
)


def _failure_service(session: AsyncSession, user: AuthenticatedUser) -> FailureService:
    return FailureService(session, user)


def _gap_service(
    session: AsyncSession, user: AuthenticatedUser
) -> CapabilityGapService:
    return CapabilityGapService(session, user)


@router.get("/api/v1/failures", response_model=list[FailureDetailResponse])
async def list_failures(
    filters: Annotated[FailureListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(management_dependency)],
) -> list[FailureDetailResponse]:
    try:
        failures = await _failure_service(session, user).list(filters)
    except FailurePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from None
    return [FailureDetailResponse.model_validate(item) for item in failures]


@router.get("/api/v1/failures/{failure_id}", response_model=FailureDetailResponse)
async def get_failure(
    failure_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(management_dependency)],
) -> FailureDetailResponse:
    try:
        failure = await _failure_service(session, user).get(failure_id)
    except FailurePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from None
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Failure log not found"
        ) from None
    return FailureDetailResponse.model_validate(failure)


@router.get(
    "/api/v1/capability-gaps", response_model=list[CapabilityGapSummaryResponse]
)
async def list_capability_gaps(
    filters: Annotated[CapabilityGapListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(management_dependency)],
) -> list[CapabilityGapSummaryResponse]:
    try:
        gaps = await _gap_service(session, user).list(filters)
    except FailurePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from None
    return [CapabilityGapSummaryResponse.model_validate(item) for item in gaps]


@router.get(
    "/api/v1/capability-gaps/{gap_id}", response_model=CapabilityGapDetailResponse
)
async def get_capability_gap(
    gap_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(management_dependency)],
) -> CapabilityGapDetailResponse:
    try:
        gap = await _gap_service(session, user).get(gap_id)
    except FailurePermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from None
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capability gap not found"
        ) from None
    return CapabilityGapDetailResponse.model_validate(gap)


@router.post(
    "/api/v1/capability-gaps/{gap_id}/status",
    response_model=CapabilityGapDetailResponse,
)
async def update_capability_gap_status(
    gap_id: UUID,
    payload: CapabilityGapStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(require_company_account)],
) -> CapabilityGapDetailResponse:
    try:
        gap = await _gap_service(session, user).update_status(gap_id, payload)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Capability gap not found"
        ) from None
    return CapabilityGapDetailResponse.model_validate(gap)
