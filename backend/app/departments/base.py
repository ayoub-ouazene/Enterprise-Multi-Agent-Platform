from typing import ClassVar, Protocol, runtime_checkable

from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionContext,
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentExecutionUpdates,
    DepartmentNextAction,
    DepartmentStateUpdates,
)
from app.departments.exceptions import DepartmentContextMismatchError


@runtime_checkable
class DepartmentAgent(Protocol):
    """Stateless contract implemented by every Version 1 department agent."""

    department_type: DepartmentType

    async def execute(
        self,
        context: DepartmentExecutionContext,
    ) -> DepartmentExecutionResult:
        ...


class DeterministicPlaceholderDepartmentAgent:
    """Shared deterministic behavior; real department intelligence comes later."""

    department_type: ClassVar[DepartmentType]
    department_label: ClassVar[str]
    completed_step: ClassVar[str]

    async def execute(
        self,
        context: DepartmentExecutionContext,
    ) -> DepartmentExecutionResult:
        if context.active_department_type != self.department_type:
            raise DepartmentContextMismatchError(
                "The active department does not match the resolved implementation"
            )
        reason = f"{self.department_label} execution foundation validated."
        return DepartmentExecutionResult(
            department_type=self.department_type,
            status=DepartmentExecutionStatus.COMPLETED,
            decision="placeholder_execution_completed",
            reason=reason,
            user_message=(
                f"The {self.department_label} placeholder completed its "
                "foundation check."
            ),
            current_stage=f"{self.department_type.value}_placeholder_completed",
            completed_step=self.completed_step,
            next_action=DepartmentNextAction.COMPLETE_REQUEST,
            is_terminal=True,
            safe_event_title=f"{self.department_label} stage completed",
            safe_event_message=reason,
            state_updates=DepartmentStateUpdates(
                execution=DepartmentExecutionUpdates(
                    last_operation=f"{self.department_type.value}_placeholder",
                    last_operation_status="completed",
                )
            ),
        )
