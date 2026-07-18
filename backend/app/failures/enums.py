from enum import StrEnum


class FailureType(StrEnum):
    TOOL_FAILURE = "tool_failure"
    DATABASE_FAILURE = "database_failure"
    RETRIEVAL_FAILURE = "retrieval_failure"
    EXTERNAL_SERVICE_FAILURE = "external_service_failure"
    VALIDATION_FAILURE = "validation_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
    WORKFLOW_FAILURE = "workflow_failure"
    CONFIGURATION_FAILURE = "configuration_failure"
    UNEXPECTED_FAILURE = "unexpected_failure"


class FailureSource(StrEnum):
    API = "api"
    SERVICE = "service"
    REPOSITORY = "repository"
    TOOL = "tool"
    WORKFLOW = "workflow"
    RAG = "rag"
    LLM = "llm"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"


class CapabilityGapStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    PLANNED = "planned"
    RESOLVED = "resolved"
    REJECTED = "rejected"


UNRESOLVED_GAP_STATUSES = frozenset(
    {
        CapabilityGapStatus.OPEN,
        CapabilityGapStatus.ACKNOWLEDGED,
        CapabilityGapStatus.PLANNED,
    }
)
