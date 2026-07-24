from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.database.session import get_db_session
from app.human_actions.schemas import (
    HumanActionCreate,
    HumanActionListFilters,
    HumanActionResponse,
    HumanActionSubmitPayload,
    HumanActionSubmitResponse,
)
from app.human_actions.service import (
    HumanActionPermissionError,
    HumanActionService,
)

router = APIRouter(prefix="/api/v1/human-actions", tags=["human-actions"])


def _service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> HumanActionService:
    return HumanActionService(session, current_user)


@router.get("", response_model=list[HumanActionResponse])
async def list_human_actions(
    filters: Annotated[HumanActionListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[HumanActionResponse]:
    actions = await _service(session, current_user).list(filters)
    return [HumanActionResponse.model_validate(item) for item in actions]


@router.get("/{action_id}", response_model=HumanActionResponse)
async def get_human_action(
    action_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> HumanActionResponse:
    try:
        action = await _service(session, current_user).get(action_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human action not found",
        ) from None
    return HumanActionResponse.model_validate(action)


@router.post("", response_model=HumanActionResponse, status_code=status.HTTP_201_CREATED)
async def create_human_action(
    payload: HumanActionCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> HumanActionResponse:
    try:
        action = await _service(session, current_user).create(payload)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business request not found",
        ) from None
    except HumanActionPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
    return HumanActionResponse.model_validate(action)


@router.post(
    "/{action_id}/submit",
    response_model=HumanActionSubmitResponse,
)
async def submit_human_action(
    action_id: UUID,
    payload: HumanActionSubmitPayload,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> HumanActionSubmitResponse:
    try:
        return await _service(session, current_user).submit(action_id, payload)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Human action not found",
        ) from None
    except BusinessValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from None
    except HumanActionPermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
