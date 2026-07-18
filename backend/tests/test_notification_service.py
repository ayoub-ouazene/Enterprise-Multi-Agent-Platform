import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ActorType
from app.core.exceptions import BusinessValidationError, NotFoundError
from app.notifications.enums import NotificationSeverity, NotificationType
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationCreate, NotificationListFilters
from app.notifications.service import NotificationService
from app.requests.enums import RequestStatus
from app.requests.repository import BusinessRequestRepository
from app.users.repository import UserRepository


def recipient(company_id, *, user_id=None, actor_type=ActorType.EMPLOYEE):
    return SimpleNamespace(
        id=user_id or uuid4(),
        company_id=company_id,
        email="recipient@example.com",
        actor_type=actor_type,
        employee=SimpleNamespace(id=uuid4(), department_id=None)
        if actor_type != ActorType.COMPANY
        else None,
    )


def request_record(company_id, requester_user_id, **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "requester_user_id": requester_user_id,
        "owner_department_id": None,
        "active_department_id": None,
        "status": RequestStatus.CREATED,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def notification_record(company_id, recipient_user_id, request_id=None):
    return SimpleNamespace(
        id=uuid4(),
        company_id=company_id,
        recipient_user_id=recipient_user_id,
        request_id=request_id,
        notification_type=NotificationType.REQUEST_CREATED,
        title="Request created",
        message="Your request has been created.",
        severity=NotificationSeverity.INFO,
        action_required=False,
        action_type=None,
        action_url=None,
        notification_metadata={},
        is_read=False,
        read_at=None,
        created_at=datetime.now(UTC),
        expires_at=None,
    )


def service_fixture(company_id, *, user=None, request=None, notification=None):
    session = AsyncMock(spec=AsyncSession)
    repository = Mock(spec=NotificationRepository)
    repository.create = AsyncMock(return_value=notification)
    repository.list_for_recipient = AsyncMock(return_value=[])
    repository.count_unread = AsyncMock(return_value=0)
    repository.mark_read = AsyncMock(return_value=notification)
    repository.mark_all_read = AsyncMock(return_value=0)
    user_repository = Mock(spec=UserRepository)
    user_repository.get_by_id_with_employee = AsyncMock(return_value=user)
    request_repository = Mock(spec=BusinessRequestRepository)
    request_repository.get_by_id = AsyncMock(return_value=request)
    service = NotificationService(
        session,
        company_id,
        repository,
        user_repository,
        request_repository,
    )
    return service, session, repository, user_repository, request_repository


def test_create_validates_recipient_request_and_commits() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    request = request_record(company_id, user.id)
    notification = notification_record(company_id, user.id, request.id)
    service, session, repository, user_repository, request_repository = service_fixture(
        company_id,
        user=user,
        request=request,
        notification=notification,
    )
    payload = NotificationCreate(
        recipient_user_id=user.id,
        request_id=request.id,
        notification_type=NotificationType.REQUEST_CREATED,
        title="Request created",
        message="Your request has been created.",
    )

    result = asyncio.run(service.create(payload))

    assert result is notification
    user_repository.get_by_id_with_employee.assert_awaited_once_with(user.id)
    request_repository.get_by_id.assert_awaited_once_with(request.id)
    repository.create.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_nonexistent_or_cross_company_recipient_is_rejected() -> None:
    company_id = uuid4()
    service, session, repository, _, _ = service_fixture(company_id, user=None)
    payload = NotificationCreate(
        recipient_user_id=uuid4(),
        notification_type=NotificationType.SYSTEM_NOTICE,
        title="Notice",
        message="Safe notice.",
    )

    with pytest.raises(NotFoundError):
        asyncio.run(service.create(payload))

    repository.create.assert_not_awaited()
    session.rollback.assert_awaited_once()


def test_cross_company_request_reference_is_rejected() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    service, _, repository, _, _ = service_fixture(
        company_id,
        user=user,
        request=None,
    )
    payload = NotificationCreate(
        recipient_user_id=user.id,
        request_id=uuid4(),
        notification_type=NotificationType.REQUEST_STATUS_CHANGED,
        title="Request updated",
        message="Your request was updated.",
    )

    with pytest.raises(NotFoundError):
        asyncio.run(service.create(payload))

    repository.create.assert_not_awaited()


def test_recipient_must_be_allowed_to_view_referenced_request() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    request = request_record(company_id, uuid4())
    service, _, repository, _, _ = service_fixture(
        company_id,
        user=user,
        request=request,
    )
    payload = NotificationCreate(
        recipient_user_id=user.id,
        request_id=request.id,
        notification_type=NotificationType.REQUEST_STATUS_CHANGED,
        title="Request updated",
        message="The request was updated.",
    )

    with pytest.raises(NotFoundError):
        asyncio.run(service.create(payload))

    repository.create.assert_not_awaited()


def test_request_created_helper_uses_safe_fixed_content_without_committing() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    request = request_record(company_id, user.id)
    notification = notification_record(company_id, user.id, request.id)
    service, session, repository, _, _ = service_fixture(
        company_id,
        user=user,
        request=request,
        notification=notification,
    )

    asyncio.run(service.notify_request_created(request, commit=False))

    values = repository.create.await_args.kwargs
    assert values["notification_type"] == NotificationType.REQUEST_CREATED
    assert values["severity"] == NotificationSeverity.INFO
    assert values["action_required"] is False
    assert values["message"] == "Your request has been created."
    session.commit.assert_not_awaited()


@pytest.mark.parametrize(
    ("status", "notification_type", "severity"),
    [
        (
            RequestStatus.COMPLETED,
            NotificationType.REQUEST_COMPLETED,
            NotificationSeverity.SUCCESS,
        ),
        (
            RequestStatus.REJECTED,
            NotificationType.REQUEST_REJECTED,
            NotificationSeverity.WARNING,
        ),
        (
            RequestStatus.FAILED,
            NotificationType.REQUEST_FAILED,
            NotificationSeverity.ERROR,
        ),
    ],
)
def test_terminal_notification_helper(status, notification_type, severity) -> None:
    company_id = uuid4()
    user = recipient(company_id)
    request = request_record(company_id, user.id, status=status)
    notification = notification_record(company_id, user.id, request.id)
    service, _, repository, _, _ = service_fixture(
        company_id,
        user=user,
        request=request,
        notification=notification,
    )

    asyncio.run(service.notify_terminal_request(request, status, commit=False))

    values = repository.create.await_args.kwargs
    assert values["notification_type"] == notification_type
    assert values["severity"] == severity


def test_terminal_notification_rejects_nonterminal_status() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    request = request_record(company_id, user.id)
    service, _, repository, _, _ = service_fixture(company_id)

    with pytest.raises(BusinessValidationError):
        asyncio.run(
            service.notify_terminal_request(
                request,
                RequestStatus.PROCESSING,
                commit=False,
            )
        )

    repository.create.assert_not_awaited()


def test_list_and_unread_count_use_only_supplied_authenticated_user() -> None:
    company_id = uuid4()
    user_id = uuid4()
    service, _, repository, _, _ = service_fixture(company_id)
    repository.count_unread.return_value = 4
    filters = NotificationListFilters(limit=25, offset=5)

    asyncio.run(service.list_for_user(user_id, filters))
    count = asyncio.run(service.unread_count(user_id))

    assert count == 4
    assert repository.list_for_recipient.await_args.args[0] == user_id
    assert repository.list_for_recipient.await_args.kwargs["limit"] == 25
    assert repository.list_for_recipient.await_args.kwargs["offset"] == 5
    repository.count_unread.assert_awaited_once_with(user_id)


def test_mark_read_and_mark_all_control_transactions() -> None:
    company_id = uuid4()
    user_id = uuid4()
    notification = notification_record(company_id, user_id)
    service, session, repository, _, _ = service_fixture(
        company_id,
        notification=notification,
    )
    repository.mark_all_read.return_value = 2

    result = asyncio.run(service.mark_read(notification.id, user_id))
    count = asyncio.run(service.mark_all_read(user_id))

    assert result is notification
    assert count == 2
    read_at = repository.mark_read.await_args.args[2]
    assert read_at.tzinfo is not None
    repository.mark_all_read.assert_awaited_once()
    assert session.commit.await_count == 2


def test_create_rolls_back_when_repository_fails() -> None:
    company_id = uuid4()
    user = recipient(company_id)
    service, session, repository, _, _ = service_fixture(company_id, user=user)
    repository.create.side_effect = RuntimeError("simulated notification failure")
    payload = NotificationCreate(
        recipient_user_id=user.id,
        notification_type=NotificationType.SYSTEM_NOTICE,
        title="Notice",
        message="Safe notice.",
    )

    with pytest.raises(RuntimeError, match="simulated notification failure"):
        asyncio.run(service.create(payload))

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
