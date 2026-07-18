from enum import StrEnum


class RequestStatus(StrEnum):
    CREATED = "created"
    ROUTING = "routing"
    PROCESSING = "processing"
    WAITING_FOR_DEPARTMENT = "waiting_for_department"
    WAITING_FOR_HUMAN_APPROVAL = "waiting_for_human_approval"
    WAITING_FOR_HUMAN_ACTION = "waiting_for_human_action"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RequestPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


TERMINAL_REQUEST_STATUSES = frozenset(
    {
        RequestStatus.COMPLETED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
        RequestStatus.FAILED,
    }
)
