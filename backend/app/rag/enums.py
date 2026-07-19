from enum import StrEnum


class KnowledgeDocumentType(StrEnum):
    POLICY = "policy"
    PROCEDURE = "procedure"
    MANUAL = "manual"
    FAQ = "faq"
    PRODUCT_DOCUMENTATION = "product_documentation"
    TROUBLESHOOTING_GUIDE = "troubleshooting_guide"
    BENEFITS_DOCUMENT = "benefits_document"
    INTERNAL_RULE = "internal_rule"
    OTHER = "other"


class KnowledgeDepartmentScope(StrEnum):
    SHARED = "shared"
    CUSTOMER_SUPPORT = "customer_support"
    HR = "hr"
    IT = "it"
    FINANCE = "finance"
    PROCUREMENT = "procurement"


class KnowledgeAccessScope(StrEnum):
    ALL_AUTHENTICATED = "all_authenticated"
    EMPLOYEES = "employees"
    DEPARTMENT_MANAGERS = "department_managers"
    COMPANY_ACCOUNT = "company_account"
    INTERNAL_SYSTEM = "internal_system"


class KnowledgeDocumentStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class KnowledgeIngestionStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
