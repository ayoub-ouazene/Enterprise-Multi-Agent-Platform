from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentExecutionResult
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.hr.service import HRService


class HRDepartmentAgent:
    """Real Step 17 HR implementation."""

    department_type = DepartmentType.HR

    def __init__(self, service: HRService | None = None) -> None:
        self.service = service

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        if context.active_department_type != DepartmentType.HR:
            raise DepartmentContextMismatchError("The active department does not match HR")
        if self.service is None:
            raise RuntimeError("HR dependencies are unavailable")
        return await self.service.execute(context)
