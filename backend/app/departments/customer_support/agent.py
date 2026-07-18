from app.core.enums import DepartmentType
from app.departments.base import DeterministicPlaceholderDepartmentAgent


class CustomerSupportDepartmentAgent(DeterministicPlaceholderDepartmentAgent):
    """Step 11 placeholder; it contains no Customer Support business logic."""

    department_type = DepartmentType.CUSTOMER_SUPPORT
    department_label = "Customer Support"
    completed_step = "customer_support_placeholder_completed"
