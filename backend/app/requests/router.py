from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.database.session import get_db_session
from app.requests.schemas import (
    BusinessRequestCancellationResponse,
    BusinessRequestCreate,
    BusinessRequestDetailResponse,
    BusinessRequestListFilters,
    BusinessRequestSummaryResponse,
)
from app.requests.service import (
    BusinessRequestService,
    RequestPermissionError,
)
from app.workflow.enums import WorkflowEventType
from app.workflow.schemas import WorkflowEventPublicResponse
from app.workflow.service import WorkflowEventService


router = APIRouter(prefix="/api/v1/requests", tags=["business-requests"])


def _service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> BusinessRequestService:
    return BusinessRequestService(session, current_user)


def _workflow_event_service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> WorkflowEventService:
    return WorkflowEventService(session, current_user)


@router.post(
    "",
    response_model=BusinessRequestDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: BusinessRequestCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> BusinessRequestDetailResponse:
    try:
        business_request = await _service(session, current_user).create(payload)
    except RequestPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
    return BusinessRequestDetailResponse.model_validate(business_request)


@router.get("", response_model=list[BusinessRequestSummaryResponse])
async def list_requests(
    filters: Annotated[BusinessRequestListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[BusinessRequestSummaryResponse]:
    requests = await _service(session, current_user).list(filters)
    return [BusinessRequestSummaryResponse.model_validate(item) for item in requests]


@router.get(
    "/{request_id}/events",
    response_model=list[WorkflowEventPublicResponse],
)
async def list_request_events(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    event_type: Annotated[WorkflowEventType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WorkflowEventPublicResponse]:
    try:
        return await _workflow_event_service(session, current_user).timeline(
            request_id,
            event_type=event_type,
            limit=limit,
            offset=offset,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business request not found",
        ) from None


@router.get("/{request_id}", response_model=BusinessRequestDetailResponse)
async def get_request(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> BusinessRequestDetailResponse:
    try:
        business_request = await _service(session, current_user).get(request_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business request not found",
        ) from None
    return BusinessRequestDetailResponse.model_validate(business_request)


@router.post(
    "/{request_id}/cancel",
    response_model=BusinessRequestCancellationResponse,
)
async def cancel_request(
    request_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> BusinessRequestCancellationResponse:
    try:
        business_request = await _service(session, current_user).cancel(request_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business request not found",
        ) from None
    except BusinessValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None
    return BusinessRequestCancellationResponse.model_validate(business_request)
