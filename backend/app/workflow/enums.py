from enum import StrEnum


class WorkflowEventType(StrEnum):
    REQUEST_CREATED = "request_created"
    ROUTING_STARTED = "routing_started"
    REQUEST_ROUTED = "request_routed"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    DEPARTMENT_COLLABORATION_STARTED = "department_collaboration_started"
    DEPARTMENT_COLLABORATION_COMPLETED = "department_collaboration_completed"
    WAITING_FOR_HUMAN_APPROVAL = "waiting_for_human_approval"
    WAITING_FOR_HUMAN_ACTION = "waiting_for_human_action"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    REQUEST_RESUMED = "request_resumed"
    REQUEST_COMPLETED = "request_completed"
    REQUEST_REJECTED = "request_rejected"
    REQUEST_CANCELLED = "request_cancelled"
    REQUEST_FAILED = "request_failed"
    FAILURE_RECORDED = "failure_recorded"
    CAPABILITY_GAP_DETECTED = "capability_gap_detected"


class WorkflowEventActorType(StrEnum):
    SYSTEM = "system"
    ROUTER = "router"
    DEPARTMENT_AGENT = "department_agent"
    REVIEWER = "reviewer"
    USER = "user"
    MANAGER = "manager"
    COMPANY_ACCOUNT = "company_account"
    TOOL = "tool"


class WorkflowEventVisibility(StrEnum):
    REQUESTER = "requester"
    MANAGER = "manager"
    COMPANY = "company"
    INTERNAL = "internal"
