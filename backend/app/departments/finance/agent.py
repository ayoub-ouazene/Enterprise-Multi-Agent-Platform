from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentExecutionResult
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.finance.service import FinanceService


class FinanceDepartmentAgent:
    """Real Step 15 Finance implementation."""

    department_type = DepartmentType.FINANCE

    def __init__(self, service: FinanceService | None = None) -> None:
        self.service = service

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        if context.active_department_type != DepartmentType.FINANCE:
            raise DepartmentContextMismatchError("The active department does not match Finance")
        if self.service is None:
            raise RuntimeError("Finance dependencies are unavailable")
        return await self.service.execute(context)
