from sqlalchemy import CheckConstraint, inspect

from app.database import models as database_models
from app.notifications.enums import (
    NotificationActionType,
    NotificationSeverity,
    NotificationType,
)
from app.notifications.models import Notification


def test_notification_model_has_required_fields_and_relationships() -> None:
    mapper = inspect(Notification)

    assert set(mapper.columns.keys()) == {
        "id",
        "company_id",
        "recipient_user_id",
        "request_id",
        "notification_type",
        "title",
        "message",
        "severity",
        "action_required",
        "action_type",
        "action_url",
        "notification_metadata",
        "is_read",
        "read_at",
        "created_at",
        "expires_at",
    }
    assert mapper.columns["notification_metadata"].name == "metadata"
    assert set(mapper.relationships.keys()) == {
        "company",
        "recipient",
        "business_request",
    }
    assert database_models.Notification is Notification


def test_notification_constraints_preserve_read_and_action_consistency() -> None:
    constraint_names = {
        constraint.name
        for constraint in Notification.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_notifications_required_action_type" in constraint_names
    assert "ck_notifications_read_timestamp" in constraint_names


def test_notification_enums_are_closed() -> None:
    assert {item.value for item in NotificationSeverity} == {
        "info",
        "success",
        "warning",
        "error",
    }
    assert NotificationType.REQUEST_CREATED.value == "request_created"
    assert NotificationType.CAPABILITY_GAP.value == "capability_gap"
    assert NotificationActionType.VIEW_REQUEST.value == "view_request"
