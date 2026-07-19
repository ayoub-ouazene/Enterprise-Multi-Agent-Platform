from enum import StrEnum


class ITRequestCategory(StrEnum):
    IT_INFORMATION = "it_information"
    SOFTWARE_ACCESS = "software_access"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_UNLOCK = "account_unlock"
    ACCOUNT_PROVISIONING = "account_provisioning"
    MFA_ACCESS = "mfa_access"
    HARDWARE_REQUEST = "hardware_request"
    SOFTWARE_INSTALLATION = "software_installation"
    EMPLOYEE_INCIDENT = "employee_incident"
    EXTERNAL_CUSTOMER_INCIDENT = "external_customer_incident"
    ASSET_ASSIGNMENT = "asset_assignment"
    HUMAN_TECHNICIAN_ESCALATION = "human_technician_escalation"
    UNSUPPORTED = "unsupported"


class ITDecision(StrEnum):
    ANSWER = "answer"
    PREPARE_ACCESS = "prepare_access"
    PREPARE_OPERATION = "prepare_operation"
    DIAGNOSE = "diagnose"
    RESOLVE = "resolve"
    CLARIFY = "clarify"
    USE_TOOL = "use_tool"
    PREPARE_FINANCE = "prepare_finance"
    PREPARE_PROCUREMENT = "prepare_procurement"
    PREPARE_HUMAN_ACTION = "prepare_human_action"
    UNSUPPORTED = "unsupported"


class AccessType(StrEnum):
    SOFTWARE = "software"
    ACCOUNT = "account"
    PASSWORD_RESET = "password_reset"
    ACCOUNT_UNLOCK = "account_unlock"
    MFA = "mfa"


class PolicyDecision(StrEnum):
    PENDING = "pending"
    ALLOWED = "allowed"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"


class ProvisioningStatus(StrEnum):
    PENDING = "pending"
    PREPARED = "prepared"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class HardwareAssignmentStatus(StrEnum):
    PENDING = "pending"
    INVENTORY_CHECKED = "inventory_checked"
    ASSET_AVAILABLE = "asset_available"
    WAITING_BUDGET = "waiting_budget"
    WAITING_PROCUREMENT = "waiting_procurement"
    WAITING_HUMAN = "waiting_human"
    PREPARED = "prepared"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetStatus(StrEnum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    LOST = "lost"


class IncidentSource(StrEnum):
    EMPLOYEE = "employee"
    CUSTOMER_SUPPORT = "customer_support"
    INTERNAL = "internal"


class IncidentStatus(StrEnum):
    NEW = "new"
    DIAGNOSING = "diagnosing"
    WAITING_USER = "waiting_user"
    WAITING_TECHNICIAN = "waiting_technician"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FAILED = "failed"


class ImpactLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ITModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
