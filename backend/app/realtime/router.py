from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.auth.context import AuthenticatedUser
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.database.session import AsyncSessionFactory
from app.realtime.dependencies import get_current_user_for_sse
from app.realtime.service import (
    _authorize_request_access,
    _session_factory,
    _settings,
    notification_stream,
    workflow_event_stream,
)

router = APIRouter(prefix="/api/v1", tags=["realtime"])


@router.get("/requests/{request_id}/events/stream")
async def stream_request_events(
    request: Request,
    request_id: UUID,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_for_sse)],
    last_event_id: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    """Stream workflow events for a business request via Server-Sent Events.

    - Authentication: Bearer token header OR `?token=<jwt>` query param.
    - Replay: pass `last_event_id` query param (or rely on browser `Last-Event-ID`).
    - Heartbeat: sent every `sse_heartbeat_seconds` to keep connection alive.
    """
    settings = _settings(request)
    session_factory = _session_factory(request)

    # Authorize before streaming so NotFoundError becomes HTTP 404
    async with session_factory() as session:
        try:
            await _authorize_request_access(session, current_user, request_id)
        except NotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business request not found",
            ) from None

    async def event_generator():
        async for line in workflow_event_stream(
            session_factory,
            current_user,
            request_id,
            heartbeat_seconds=settings.sse_heartbeat_seconds,
            last_event_id=last_event_id,
        ):
            yield line

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/notifications/stream")
async def stream_notifications(
    request: Request,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user_for_sse)],
    last_event_id: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    """Stream new notifications for the authenticated user via Server-Sent Events.

    - Authentication: Bearer token header OR `?token=<jwt>` query param.
    - Replay: pass `last_event_id` query param (or rely on browser `Last-Event-ID`).
    - Notifications are delivered without marking them as read.
    """
    settings = _settings(request)
    session_factory = _session_factory(request)

    async def event_generator():
        async for line in notification_stream(
            session_factory,
            current_user,
            heartbeat_seconds=settings.sse_heartbeat_seconds,
            last_event_id=last_event_id,
        ):
            yield line

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
