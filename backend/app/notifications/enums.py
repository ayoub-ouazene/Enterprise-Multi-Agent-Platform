from enum import StrEnum


class NotificationType(StrEnum):
    REQUEST_CREATED = "request_created"
    REQUEST_STATUS_CHANGED = "request_status_changed"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_REJECTED = "request_rejected"
    REQUEST_CANCELLED = "request_cancelled"
    REQUEST_FAILED = "request_failed"
    APPROVAL_REQUIRED = "approval_required"
    HUMAN_ACTION_REQUIRED = "human_action_required"
    INFORMATION_REQUIRED = "information_required"
    REVIEW_COMPLETED = "review_completed"
    CAPABILITY_GAP = "capability_gap"
    SYSTEM_NOTICE = "system_notice"
    IMPORT_VALIDATION_COMPLETED = "import_validation_completed"
    IMPORT_COMPLETED = "import_completed"
    IMPORT_FAILED = "import_failed"
    ONBOARDING_ACTIVATION_READY = "onboarding_activation_ready"
    ONBOARDING_ACTIVATION_BLOCKED = "onboarding_activation_blocked"
    COMPANY_ACTIVATED = "company_activated"


class NotificationSeverity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationActionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    PROVIDE_INFORMATION = "provide_information"
    CONFIRM_ACTION = "confirm_action"
    VIEW_REQUEST = "view_request"
    OPEN_ONBOARDING = "open_onboarding"
    REVIEW_FAILURE = "review_failure"
