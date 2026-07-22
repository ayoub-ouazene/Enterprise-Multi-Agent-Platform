from enum import StrEnum


class ImportType(StrEnum):
    EMPLOYEES = "employees"
    DEPARTMENTS = "departments"
    MANAGER_ASSIGNMENTS = "manager_assignments"
    ASSETS = "assets"
    SOFTWARE_CATALOG = "software_catalog"
    BUDGETS = "budgets"
    SUPPLIER_CANDIDATES = "supplier_candidates"
    COMPANY_HOLIDAYS = "company_holidays"
    STAFFING_RULES = "staffing_rules"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
