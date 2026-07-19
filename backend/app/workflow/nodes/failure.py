from typing import Any
from app.departments.contracts import DepartmentExecutionResult, DepartmentExecutionStatus
from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def terminal_failure_node(state: WorkflowState) -> dict[str, Any]:
    result = DepartmentExecutionResult.model_validate(state.execution.department_result)
    if result.status == DepartmentExecutionStatus.UNSUPPORTED:
        return {}
    raise InactiveWorkflowNodeError("Operational graph failures are handled by WorkflowService")
