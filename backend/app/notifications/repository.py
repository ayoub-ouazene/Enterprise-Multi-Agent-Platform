from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.enums import (
    NotificationActionType,
    NotificationSeverity,
    NotificationType,
)
from app.notifications.models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession, company_id: UUID) -> None:
        self.session = session
        self.company_id = company_id

    @staticmethod
    def _active_condition():
        return or_(
            Notification.expires_at.is_(None),
            Notification.expires_at > func.now(),
        )

    async def create(
        self,
        *,
        recipient_user_id: UUID,
        request_id: UUID | None,
        notification_type: NotificationType,
        title: str,
        message: str,
        severity: NotificationSeverity,
        action_required: bool,
        action_type: NotificationActionType | None,
        action_url: str | None,
        metadata: dict[str, object],
        expires_at: datetime | None,
    ) -> Notification:
        notification = Notification(
            company_id=self.company_id,
            recipient_user_id=recipient_user_id,
            request_id=request_id,
            notification_type=notification_type,
            title=title,
            message=message,
            severity=severity,
            action_required=action_required,
            action_type=action_type,
            action_url=action_url,
            notification_metadata=metadata,
            is_read=False,
            read_at=None,
            expires_at=expires_at,
        )
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_for_recipient(
        self,
        notification_id: UUID,
        recipient_user_id: UUID,
    ) -> Notification | None:
        return await self.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.company_id == self.company_id,
                Notification.recipient_user_id == recipient_user_id,
            )
        )

    async def list_for_recipient(
        self,
        recipient_user_id: UUID,
        *,
        notification_type: NotificationType | None = None,
        severity: NotificationSeverity | None = None,
        is_read: bool | None = None,
        request_id: UUID | None = None,
        include_expired: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        statement = select(Notification).where(
            Notification.company_id == self.company_id,
            Notification.recipient_user_id == recipient_user_id,
        )
        if notification_type is not None:
            statement = statement.where(
                Notification.notification_type == notification_type
            )
        if severity is not None:
            statement = statement.where(Notification.severity == severity)
        if is_read is not None:
            statement = statement.where(Notification.is_read == is_read)
        if request_id is not None:
            statement = statement.where(Notification.request_id == request_id)
        if not include_expired:
            statement = statement.where(self._active_condition())

        result = await self.session.scalars(
            statement.order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def count_unread(self, recipient_user_id: UUID) -> int:
        count = await self.session.scalar(
            select(func.count(Notification.id)).where(
                Notification.company_id == self.company_id,
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
                self._active_condition(),
            )
        )
        return int(count or 0)

    async def mark_read(
        self,
        notification_id: UUID,
        recipient_user_id: UUID,
        read_at: datetime,
    ) -> Notification | None:
        notification = await self.session.scalar(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.company_id == self.company_id,
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=read_at)
            .returning(Notification)
        )
        if notification is not None:
            return notification
        return await self.get_for_recipient(notification_id, recipient_user_id)

    async def mark_all_read(
        self,
        recipient_user_id: UUID,
        read_at: datetime,
    ) -> int:
        result = await self.session.execute(
            update(Notification)
            .where(
                Notification.company_id == self.company_id,
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
                self._active_condition(),
            )
            .values(is_read=True, read_at=read_at)
        )
        return int(result.rowcount or 0)
