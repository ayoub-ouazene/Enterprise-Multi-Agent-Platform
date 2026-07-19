from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentExecutionResult
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.it.service import ITService


class ITDepartmentAgent:
    """Real Step 14 IT implementation."""

    department_type = DepartmentType.IT
    def __init__(self, service: ITService | None = None) -> None:
        self.service = service

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        if context.active_department_type != DepartmentType.IT:
            raise DepartmentContextMismatchError("The active department does not match IT")
        if self.service is None:
            raise RuntimeError("IT dependencies are unavailable")
        return await self.service.execute(context)
