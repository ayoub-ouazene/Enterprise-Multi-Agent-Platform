from app.core.enums import DepartmentType
from app.departments.base import DeterministicPlaceholderDepartmentAgent


class ITDepartmentAgent(DeterministicPlaceholderDepartmentAgent):
    """Step 11 placeholder; it contains no IT business logic."""

    department_type = DepartmentType.IT
    department_label = "IT"
    completed_step = "it_placeholder_completed"
