from app.core.enums import DepartmentType
from app.departments.base import DeterministicPlaceholderDepartmentAgent


class HRDepartmentAgent(DeterministicPlaceholderDepartmentAgent):
    """Step 11 placeholder; it contains no HR business logic."""

    department_type = DepartmentType.HR
    department_label = "HR"
    completed_step = "hr_placeholder_completed"
