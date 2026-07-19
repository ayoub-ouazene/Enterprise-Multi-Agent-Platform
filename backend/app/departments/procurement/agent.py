from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext, DepartmentExecutionResult
from app.departments.exceptions import DepartmentContextMismatchError
from app.departments.procurement.service import ProcurementService


class ProcurementDepartmentAgent:
    """Real Step 16 Procurement implementation."""

    department_type = DepartmentType.PROCUREMENT

    def __init__(self, service: ProcurementService | None = None) -> None:
        self.service = service

    async def execute(
        self, context: DepartmentExecutionContext
    ) -> DepartmentExecutionResult:
        if context.active_department_type != DepartmentType.PROCUREMENT:
            raise DepartmentContextMismatchError(
                "The active department does not match Procurement"
            )
        if self.service is None:
            raise RuntimeError("Procurement dependencies are unavailable")
        return await self.service.execute(context)
