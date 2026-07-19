from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentExecutionResult
from app.departments.customer_support.service import CustomerSupportService
from app.departments.exceptions import DepartmentContextMismatchError


class CustomerSupportDepartmentAgent:
    """Real, stateless Step 13 Customer Support implementation."""

    department_type = DepartmentType.CUSTOMER_SUPPORT
    def __init__(self, service: CustomerSupportService | None = None) -> None:
        self.service = service

    async def execute(self, context: DepartmentExecutionContext) -> DepartmentExecutionResult:
        if context.active_department_type != self.department_type:
            raise DepartmentContextMismatchError(
                "The active department does not match Customer Support"
            )
        if self.service is None:
            raise RuntimeError("Customer Support dependencies are unavailable")
        return await self.service.execute(context)
