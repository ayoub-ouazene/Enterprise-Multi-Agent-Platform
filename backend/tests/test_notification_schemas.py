from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.notifications.enums import (
    NotificationActionType,
    NotificationType,
)
from app.notifications.schemas import NotificationCreate


def payload(**overrides):
    values = {
        "recipient_user_id": uuid4(),
        "notification_type": NotificationType.SYSTEM_NOTICE,
        "title": "System notice",
        "message": "A safe system notice.",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    "metadata",
    [
        {"password": "private"},
        {"nested": {"access_token": "private"}},
        {"database_url": "postgresql://private"},
        {"raw_tool_output": "private"},
        {"traceback": "private"},
    ],
)
def test_notification_metadata_rejects_prohibited_keys(metadata) -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(metadata=metadata))


def test_action_required_requires_action_type() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(action_required=True))

    notification = NotificationCreate(
        **payload(
            action_required=True,
            action_type=NotificationActionType.APPROVE,
            action_url="/requests/example",
        )
    )
    assert notification.action_type == NotificationActionType.APPROVE


@pytest.mark.parametrize("action_url", ["https://example.com", "//example.com"])
def test_action_url_must_be_a_safe_relative_path(action_url) -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(action_url=action_url))


def test_expiration_requires_timezone() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(expires_at=datetime.now()))

    notification = NotificationCreate(**payload(expires_at=datetime.now(UTC)))
    assert notification.expires_at is not None


def test_internal_creation_rejects_client_company_identity() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(company_id=uuid4()))


def test_notification_type_rejects_arbitrary_strings() -> None:
    with pytest.raises(ValidationError):
        NotificationCreate(**payload(notification_type="arbitrary"))
