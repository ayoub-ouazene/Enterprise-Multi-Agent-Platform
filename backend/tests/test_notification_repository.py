import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.notifications.enums import NotificationSeverity, NotificationType
from app.notifications.repository import NotificationRepository


def test_create_assigns_tenant_recipient_and_never_commits() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    repository = NotificationRepository(session, company_id)

    notification = asyncio.run(
        repository.create(
            recipient_user_id=recipient_id,
            request_id=None,
            notification_type=NotificationType.SYSTEM_NOTICE,
            title="System notice",
            message="A safe notice.",
            severity=NotificationSeverity.INFO,
            action_required=False,
            action_type=None,
            action_url=None,
            metadata={},
            expires_at=None,
        )
    )

    assert notification.company_id == company_id
    assert notification.recipient_user_id == recipient_id
    assert notification.is_read is False
    assert notification.read_at is None
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


def test_get_is_scoped_to_company_and_recipient() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    notification_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = None
    repository = NotificationRepository(session, company_id)

    result = asyncio.run(repository.get_for_recipient(notification_id, recipient_id))

    assert result is None
    values = list(session.scalar.await_args.args[0].compile().params.values())
    assert company_id in values
    assert recipient_id in values
    assert notification_id in values


def test_list_applies_filters_pagination_and_newest_first() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    scalar_result = Mock()
    scalar_result.all.return_value = []
    session.scalars.return_value = scalar_result
    repository = NotificationRepository(session, company_id)

    result = asyncio.run(
        repository.list_for_recipient(
            recipient_id,
            notification_type=NotificationType.REQUEST_CREATED,
            severity=NotificationSeverity.INFO,
            is_read=False,
            include_expired=False,
            limit=20,
            offset=5,
        )
    )

    assert result == []
    statement = session.scalars.await_args.args[0]
    values = list(statement.compile().params.values())
    assert company_id in values
    assert recipient_id in values
    assert NotificationType.REQUEST_CREATED in values
    assert NotificationSeverity.INFO in values
    assert "created_at DESC" in str(statement)


def test_unread_count_is_recipient_scoped_and_excludes_expired() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    session.scalar.return_value = 7
    repository = NotificationRepository(session, company_id)

    count = asyncio.run(repository.count_unread(recipient_id))

    assert count == 7
    statement = session.scalar.await_args.args[0]
    values = list(statement.compile().params.values())
    assert company_id in values
    assert recipient_id in values
    assert "expires_at" in str(statement)


def test_mark_read_is_idempotent_and_preserves_existing_timestamp() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    notification_id = uuid4()
    original_read_at = datetime.now(UTC)
    existing = SimpleNamespace(
        id=notification_id,
        is_read=True,
        read_at=original_read_at,
    )
    session = AsyncMock(spec=AsyncSession)
    session.scalar.side_effect = [None, existing]
    repository = NotificationRepository(session, company_id)

    result = asyncio.run(
        repository.mark_read(
            notification_id,
            recipient_id,
            datetime.now(UTC),
        )
    )

    assert result is existing
    assert result.read_at is original_read_at
    assert session.scalar.await_count == 2
    session.commit.assert_not_awaited()


def test_mark_all_is_recipient_scoped_and_returns_changed_count() -> None:
    company_id = uuid4()
    recipient_id = uuid4()
    session = AsyncMock(spec=AsyncSession)
    result = Mock()
    result.rowcount = 3
    session.execute.return_value = result
    repository = NotificationRepository(session, company_id)

    count = asyncio.run(repository.mark_all_read(recipient_id, datetime.now(UTC)))

    assert count == 3
    statement = session.execute.await_args.args[0]
    values = list(statement.compile().params.values())
    assert company_id in values
    assert recipient_id in values
    session.commit.assert_not_awaited()
