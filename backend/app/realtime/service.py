import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.database.session import AsyncSessionFactory
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationResponse
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.workflow.enums import WorkflowEventVisibility
from app.workflow.models import WorkflowEvent
from app.workflow.repository import WorkflowEventRepository
from app.workflow.schemas import WorkflowEventPublicResponse

logger = logging.getLogger(__name__)

# Module-local sleep reference so tests can patch it without
# breaking anyio internals used by starlette.testclient.
_sleep = asyncio.sleep

# ---- Request helpers (used by router) ---------------------------------------


def _settings(request: Any) -> Settings:
    settings: Settings | None = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("Application settings are not initialized")
    return settings


def _session_factory(request: Any) -> AsyncSessionFactory:
    session_factory: AsyncSessionFactory | None = getattr(
        request.app.state,
        "session_factory",
        None,
    )
    if session_factory is None:
        raise RuntimeError("Database session factory is not initialized")
    return session_factory


# ---- Boundary limits --------------------------------------------------------

MAX_SSE_CONNECTIONS: int = 1000
MAX_REPLAY_EVENTS: int = 250
MAX_REPLAY_NOTIFICATIONS: int = 250
POLL_INTERVAL_SECONDS: float = 1.0
SSE_BATCH_SIZE: int = 50

# ---- In-memory connection accounting (soft limit) ----------------------------

_active_connection_count: int = 0
_connection_lock = asyncio.Lock()


async def _acquire_connection() -> bool:
    async with _connection_lock:
        global _active_connection_count
        if _active_connection_count >= MAX_SSE_CONNECTIONS:
            logger.warning("SSE connection limit reached (%s)", MAX_SSE_CONNECTIONS)
            return False
        _active_connection_count += 1
        return True


async def _release_connection() -> None:
    async with _connection_lock:
        global _active_connection_count
        _active_connection_count = max(0, _active_connection_count - 1)


# ---- Visibility mapping ------------------------------------------------------


def _allowed_visibilities(user: AuthenticatedUser) -> frozenset[WorkflowEventVisibility]:
    if user.actor_type == ActorType.COMPANY:
        return frozenset(
            {
                WorkflowEventVisibility.REQUESTER,
                WorkflowEventVisibility.MANAGER,
                WorkflowEventVisibility.COMPANY,
                WorkflowEventVisibility.INTERNAL,
            }
        )
    if user.actor_type == ActorType.DEPARTMENT_MANAGER:
        return frozenset(
            {
                WorkflowEventVisibility.REQUESTER,
                WorkflowEventVisibility.MANAGER,
            }
        )
    return frozenset({WorkflowEventVisibility.REQUESTER})


# ---- SSE formatting ----------------------------------------------------------


def _format_sse(
    event_type: str,
    data: dict[str, Any],
    event_id: str | None = None,
) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")
    return "\n".join(lines)


def _heartbeat() -> str:
    return ":heartbeat\n\n"


def _error_event(message: str) -> str:
    return _format_sse("error", {"message": message}, event_id="error")


# ---- Workflow-event serialization --------------------------------------------

_ACTOR_LABELS: dict[str, str] = {
    "system": "System",
    "router": "Platform assistant",
    "department_agent": "Department",
    "reviewer": "Reviewer",
    "user": "Requester",
    "manager": "Department manager",
    "company_account": "Company account",
    "tool": "System tool",
}


def _serialize_workflow_event(event: WorkflowEvent) -> dict[str, Any]:
    return WorkflowEventPublicResponse(
        id=event.id,
        request_id=event.request_id,
        event_type=event.event_type,
        stage=event.stage,
        title=event.title,
        message=event.message,
        actor_label=_ACTOR_LABELS.get(str(event.actor_type), "Unknown"),
        department_id=event.department_id,
        event_data=event.event_data,
        sequence_number=event.sequence_number,
        created_at=event.created_at,
    ).model_dump(mode="json")


# ---- Notification serialization ----------------------------------------------


def _serialize_notification(notification: Notification) -> dict[str, Any]:
    return NotificationResponse.model_validate(notification).model_dump(mode="json")


# ---- Replay helpers ----------------------------------------------------------


def _parse_last_event_id_for_events(last_event_id: str | None) -> int | None:
    if last_event_id is None:
        return None
    try:
        return int(last_event_id)
    except ValueError:
        return None


def _parse_last_event_id_for_notifications(
    last_event_id: str | None,
) -> tuple[datetime | None, UUID | None]:
    """Cursor format: '<ISO_created_at>_<uuid>' (e.g. from timestamps)."""
    if last_event_id is None:
        return (None, None)
    parts = last_event_id.split("_", 1)
    if len(parts) != 2:
        return (None, None)
    try:
        cursor_dt = datetime.fromisoformat(parts[0])
        cursor_id = UUID(parts[1])
        return (cursor_dt, cursor_id)
    except (ValueError, TypeError):
        return (None, None)


# ---- Authorization before streaming ------------------------------------------


async def _authorize_request_access(
    session: AsyncSession,
    user: AuthenticatedUser,
    request_id: UUID,
) -> None:
    repo = BusinessRequestRepository(session, user.company_id)
    business_request = await repo.get_by_id(request_id)
    if business_request is None or not can_view_business_request(user, business_request):
        raise NotFoundError("Business request not found")


# ---- Polling generators ------------------------------------------------------


async def workflow_event_stream(
    session_factory: AsyncSessionFactory,
    user: AuthenticatedUser,
    request_id: UUID,
    heartbeat_seconds: int,
    last_event_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE lines for workflow events on a single request."""
    if not await _acquire_connection():
        yield _error_event("Server is at maximum capacity. Please retry later.")
        return

    try:
        cursor = _parse_last_event_id_for_events(last_event_id)
        allowed = _allowed_visibilities(user)

        # Replay
        replayed = 0
        if cursor is not None:
            async with session_factory() as session:
                repo = WorkflowEventRepository(session, user.company_id)
                events = await repo.list_for_request(
                    request_id,
                    visibilities=allowed,
                    limit=MAX_REPLAY_EVENTS,
                    offset=0,
                )
                for event in events:
                    if event.sequence_number > cursor and event.visibility in allowed:
                        yield _format_sse(
                            "workflow_event",
                            _serialize_workflow_event(event),
                            event_id=str(event.sequence_number),
                        )
                        replayed += 1
                        if replayed >= MAX_REPLAY_EVENTS:
                            break

        last_cursor = cursor if cursor is not None else 0
        next_heartbeat = asyncio.get_event_loop().time() + heartbeat_seconds

        while True:
            async with session_factory() as session:
                repo = WorkflowEventRepository(session, user.company_id)
                events = await repo.list_for_request(
                    request_id,
                    visibilities=allowed,
                    limit=SSE_BATCH_SIZE,
                    offset=0,
                )

            new_events = [
                event
                for event in events
                if event.sequence_number > last_cursor and event.visibility in allowed
            ]

            # Sort ascending by sequence number for stable delivery
            new_events.sort(key=lambda e: e.sequence_number)

            for event in new_events:
                yield _format_sse(
                    "workflow_event",
                    _serialize_workflow_event(event),
                    event_id=str(event.sequence_number),
                )
                last_cursor = event.sequence_number

            now = asyncio.get_event_loop().time()
            if now >= next_heartbeat:
                yield _heartbeat()
                next_heartbeat = now + heartbeat_seconds

            await _sleep(POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.debug("SSE workflow stream cancelled for request %s", request_id)
    except GeneratorExit:
        logger.debug("SSE workflow stream closed for request %s", request_id)
    except Exception:
        logger.exception("SSE workflow stream error for request %s", request_id)
        yield _error_event("Stream error")
    finally:
        await _release_connection()


async def notification_stream(
    session_factory: AsyncSessionFactory,
    user: AuthenticatedUser,
    heartbeat_seconds: int,
    last_event_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Yield SSE lines for new notifications for the authenticated user."""
    if not await _acquire_connection():
        yield _error_event("Server is at maximum capacity. Please retry later.")
        return

    try:
        cursor_dt, cursor_id = _parse_last_event_id_for_notifications(last_event_id)
        last_cursor_dt = cursor_dt
        last_cursor_id = cursor_id

        # Replay
        replayed = 0
        if cursor_dt is not None and cursor_id is not None:
            async with session_factory() as session:
                repo = NotificationRepository(session, user.company_id)
                notifications = await repo.list_for_recipient(
                    user.user_id,
                    limit=MAX_REPLAY_NOTIFICATIONS,
                    offset=0,
                )
                # Reverse because repo returns desc; we need ascending for replay
                for notification in reversed(notifications):
                    if (
                        notification.created_at > cursor_dt
                        or (
                            notification.created_at == cursor_dt
                            and notification.id > cursor_id
                        )
                    ):
                        yield _format_sse(
                            "notification",
                            _serialize_notification(notification),
                            event_id=f"{notification.created_at.isoformat()}_{notification.id}",
                        )
                        replayed += 1
                        if replayed >= MAX_REPLAY_NOTIFICATIONS:
                            break
                        if last_cursor_dt is None or notification.created_at > last_cursor_dt:
                            last_cursor_dt = notification.created_at
                            last_cursor_id = notification.id
                        elif notification.created_at == last_cursor_dt and notification.id > last_cursor_id:
                            last_cursor_id = notification.id

        next_heartbeat = asyncio.get_event_loop().time() + heartbeat_seconds

        while True:
            async with session_factory() as session:
                repo = NotificationRepository(session, user.company_id)
                notifications = await repo.list_for_recipient(
                    user.user_id,
                    limit=SSE_BATCH_SIZE,
                    offset=0,
                )

            new_notifications: list[Notification] = []
            for notification in notifications:
                is_new = False
                if last_cursor_dt is None:
                    is_new = True
                elif notification.created_at > last_cursor_dt:
                    is_new = True
                elif notification.created_at == last_cursor_dt and last_cursor_id is not None and notification.id > last_cursor_id:
                    is_new = True
                if is_new:
                    new_notifications.append(notification)

            # Sort ascending by created_at then id for stable delivery
            new_notifications.sort(key=lambda n: (n.created_at, n.id))

            for notification in new_notifications:
                yield _format_sse(
                    "notification",
                    _serialize_notification(notification),
                    event_id=f"{notification.created_at.isoformat()}_{notification.id}",
                )
                last_cursor_dt = notification.created_at
                last_cursor_id = notification.id

            now = asyncio.get_event_loop().time()
            if now >= next_heartbeat:
                yield _heartbeat()
                next_heartbeat = now + heartbeat_seconds

            await _sleep(POLL_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.debug("SSE notification stream cancelled for user %s", user.user_id)
    except GeneratorExit:
        logger.debug("SSE notification stream closed for user %s", user.user_id)
    except Exception:
        logger.exception("SSE notification stream error for user %s", user.user_id)
        yield _error_event("Stream error")
    finally:
        await _release_connection()
