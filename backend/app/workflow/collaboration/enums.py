from enum import StrEnum


class CollaborationRuntimeStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"
