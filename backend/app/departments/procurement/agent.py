from app.core.enums import DepartmentType
from app.departments.base import DeterministicPlaceholderDepartmentAgent


class ProcurementDepartmentAgent(DeterministicPlaceholderDepartmentAgent):
    """Step 11 placeholder; it contains no Procurement business logic."""

    department_type = DepartmentType.PROCUREMENT
    department_label = "Procurement"
    completed_step = "procurement_placeholder_completed"
