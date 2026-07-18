from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.context import AuthenticatedUser
from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.notifications.enums import NotificationSeverity, NotificationType
from app.notifications.models import Notification
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationCreate, NotificationListFilters
from app.requests.enums import RequestStatus
from app.requests.models import BusinessRequest
from app.requests.permissions import can_view_business_request
from app.requests.repository import BusinessRequestRepository
from app.users.models import User
from app.users.repository import UserRepository


TERMINAL_NOTIFICATION_DETAILS: dict[
    RequestStatus,
    tuple[NotificationType, NotificationSeverity, str, str],
] = {
    RequestStatus.COMPLETED: (
        NotificationType.REQUEST_COMPLETED,
        NotificationSeverity.SUCCESS,
        "Request completed",
        "Your request has been completed.",
    ),
    RequestStatus.REJECTED: (
        NotificationType.REQUEST_REJECTED,
        NotificationSeverity.WARNING,
        "Request rejected",
        "Your request has been rejected.",
    ),
    RequestStatus.FAILED: (
        NotificationType.REQUEST_FAILED,
        NotificationSeverity.ERROR,
        "Request failed",
        "Your request could not be completed.",
    ),
}


class NotificationService:
    def __init__(
        self,
        session: AsyncSession,
        company_id: UUID,
        repository: NotificationRepository | None = None,
        user_repository: UserRepository | None = None,
        request_repository: BusinessRequestRepository | None = None,
    ) -> None:
        self.session = session
        self.company_id = company_id
        self.repository = repository or NotificationRepository(session, company_id)
        self.user_repository = user_repository or UserRepository(session, company_id)
        self.request_repository = request_repository or BusinessRequestRepository(
            session,
            company_id,
        )

    def _recipient_context(self, recipient: User) -> AuthenticatedUser:
        employee = recipient.employee
        return AuthenticatedUser(
            user_id=recipient.id,
            company_id=recipient.company_id,
            email=recipient.email,
            actor_type=recipient.actor_type,
            employee_id=employee.id if employee is not None else None,
            department_id=employee.department_id if employee is not None else None,
            is_manager=recipient.actor_type == ActorType.DEPARTMENT_MANAGER,
        )

    async def create(
        self,
        payload: NotificationCreate,
        *,
        commit: bool = True,
    ) -> Notification:
        try:
            recipient = await self.user_repository.get_by_id_with_employee(
                payload.recipient_user_id
            )
            if recipient is None:
                raise NotFoundError("Notification recipient not found")

            if payload.request_id is not None:
                business_request = await self.request_repository.get_by_id(
                    payload.request_id
                )
                if business_request is None or not can_view_business_request(
                    self._recipient_context(recipient),
                    business_request,
                ):
                    raise NotFoundError("Referenced business request not found")

            notification = await self.repository.create(
                recipient_user_id=payload.recipient_user_id,
                request_id=payload.request_id,
                notification_type=payload.notification_type,
                title=payload.title,
                message=payload.message,
                severity=payload.severity,
                action_required=payload.action_required,
                action_type=payload.action_type,
                action_url=payload.action_url,
                metadata=payload.metadata,
                expires_at=payload.expires_at,
            )
            if commit:
                await self.session.commit()
                await self.session.refresh(notification)
            return notification
        except Exception:
            if commit:
                await self.session.rollback()
            raise

    async def notify_request_created(
        self,
        business_request: BusinessRequest,
        *,
        commit: bool = True,
    ) -> Notification:
        return await self.create(
            NotificationCreate(
                recipient_user_id=business_request.requester_user_id,
                request_id=business_request.id,
                notification_type=NotificationType.REQUEST_CREATED,
                title="Request created",
                message="Your request has been created.",
                severity=NotificationSeverity.INFO,
                action_required=False,
                metadata={"request_status": RequestStatus.CREATED.value},
            ),
            commit=commit,
        )

    async def notify_request_cancelled(
        self,
        business_request: BusinessRequest,
        *,
        commit: bool = True,
    ) -> Notification:
        return await self.create(
            NotificationCreate(
                recipient_user_id=business_request.requester_user_id,
                request_id=business_request.id,
                notification_type=NotificationType.REQUEST_CANCELLED,
                title="Request cancelled",
                message="Your request has been cancelled.",
                severity=NotificationSeverity.WARNING,
                action_required=False,
                metadata={"request_status": RequestStatus.CANCELLED.value},
            ),
            commit=commit,
        )

    async def notify_terminal_request(
        self,
        business_request: BusinessRequest,
        status: RequestStatus,
        *,
        commit: bool = True,
    ) -> Notification:
        details = TERMINAL_NOTIFICATION_DETAILS.get(status)
        if details is None:
            raise BusinessValidationError(
                "Terminal notifications support completed, rejected, or failed requests"
            )
        notification_type, severity, title, message = details
        return await self.create(
            NotificationCreate(
                recipient_user_id=business_request.requester_user_id,
                request_id=business_request.id,
                notification_type=notification_type,
                title=title,
                message=message,
                severity=severity,
                action_required=False,
                metadata={"request_status": status.value},
            ),
            commit=commit,
        )

    async def list_for_user(
        self,
        recipient_user_id: UUID,
        filters: NotificationListFilters,
    ) -> list[Notification]:
        return await self.repository.list_for_recipient(
            recipient_user_id,
            notification_type=filters.notification_type,
            severity=filters.severity,
            is_read=filters.is_read,
            include_expired=filters.include_expired,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def unread_count(self, recipient_user_id: UUID) -> int:
        return await self.repository.count_unread(recipient_user_id)

    async def mark_read(
        self,
        notification_id: UUID,
        recipient_user_id: UUID,
    ) -> Notification:
        try:
            notification = await self.repository.mark_read(
                notification_id,
                recipient_user_id,
                datetime.now(UTC),
            )
            if notification is None:
                raise NotFoundError("Notification not found")
            await self.session.commit()
            await self.session.refresh(notification)
            return notification
        except Exception:
            await self.session.rollback()
            raise

    async def mark_all_read(self, recipient_user_id: UUID) -> int:
        try:
            updated_count = await self.repository.mark_all_read(
                recipient_user_id,
                datetime.now(UTC),
            )
            await self.session.commit()
            return updated_count
        except Exception:
            await self.session.rollback()
            raise
