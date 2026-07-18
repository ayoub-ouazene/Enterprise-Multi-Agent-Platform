from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.auth.dependencies import require_authenticated_user
from app.core.exceptions import NotFoundError
from app.database.session import get_db_session
from app.notifications.schemas import (
    NotificationListFilters,
    NotificationResponse,
    ReadAllResponse,
    UnreadCountResponse,
)
from app.notifications.service import NotificationService


router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _service(
    session: AsyncSession,
    current_user: AuthenticatedUser,
) -> NotificationService:
    return NotificationService(session, current_user.company_id)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    filters: Annotated[NotificationListFilters, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> list[NotificationResponse]:
    notifications = await _service(session, current_user).list_for_user(
        current_user.user_id,
        filters,
    )
    return [NotificationResponse.model_validate(item) for item in notifications]


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> UnreadCountResponse:
    count = await _service(session, current_user).unread_count(current_user.user_id)
    return UnreadCountResponse(unread_count=count)


@router.post("/read-all", response_model=ReadAllResponse)
async def mark_all_notifications_read(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> ReadAllResponse:
    count = await _service(session, current_user).mark_all_read(current_user.user_id)
    return ReadAllResponse(updated_count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> NotificationResponse:
    try:
        notification = await _service(session, current_user).mark_read(
            notification_id,
            current_user.user_id,
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        ) from None
    return NotificationResponse.model_validate(notification)
