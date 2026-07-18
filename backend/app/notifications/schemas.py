from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.json_validation import (
    EVENT_PROHIBITED_KEY_PARTS,
    validate_safe_json,
)
from app.notifications.enums import (
    NotificationActionType,
    NotificationSeverity,
    NotificationType,
)


class NotificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_user_id: UUID
    request_id: UUID | None = None
    notification_type: NotificationType
    title: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1, max_length=10_000)
    severity: NotificationSeverity = NotificationSeverity.INFO
    action_required: bool = False
    action_type: NotificationActionType | None = None
    action_url: str | None = Field(default=None, max_length=2048)
    metadata: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime | None = None

    @field_validator("title", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("action_url")
    @classmethod
    def validate_action_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped.startswith("/") or stripped.startswith("//"):
            raise ValueError("action_url must be a relative application path")
        return stripped

    @field_validator("metadata")
    @classmethod
    def reject_prohibited_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_safe_json(
            value,
            path="metadata",
            forbidden_key_parts=EVENT_PROHIBITED_KEY_PARTS,
        )

    @field_validator("expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        return value

    @model_validator(mode="after")
    def require_action_type(self) -> "NotificationCreate":
        if self.action_required and self.action_type is None:
            raise ValueError("action_type is required when action_required is true")
        return self


class NotificationListFilters(BaseModel):
    notification_type: NotificationType | None = None
    severity: NotificationSeverity | None = None
    is_read: bool | None = None
    include_expired: bool = False
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: UUID | None
    notification_type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    action_required: bool
    action_type: NotificationActionType | None
    action_url: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    expires_at: datetime | None


class UnreadCountResponse(BaseModel):
    unread_count: int


class ReadAllResponse(BaseModel):
    updated_count: int
