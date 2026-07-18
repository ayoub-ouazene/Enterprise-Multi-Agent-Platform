from enum import StrEnum


class ActorType(StrEnum):
    COMPANY = "company"
    EXTERNAL_USER = "external_user"
    EMPLOYEE = "employee"
    DEPARTMENT_MANAGER = "department_manager"


class DepartmentType(StrEnum):
    CUSTOMER_SUPPORT = "customer_support"
    HR = "hr"
    IT = "it"
    FINANCE = "finance"
    PROCUREMENT = "procurement"


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_class]
