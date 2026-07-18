from app.core.enums import DepartmentType
from app.departments.base import DeterministicPlaceholderDepartmentAgent


class FinanceDepartmentAgent(DeterministicPlaceholderDepartmentAgent):
    """Step 11 placeholder; it contains no Finance business logic."""

    department_type = DepartmentType.FINANCE
    department_label = "Finance"
    completed_step = "finance_placeholder_completed"
