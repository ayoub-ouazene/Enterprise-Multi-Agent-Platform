from typing import Any
from langgraph.runtime import Runtime
from app.workflow.state import WorkflowRuntimeContext, WorkflowState
from app.workflow.exceptions import InactiveWorkflowNodeError


async def it_read_tool_node(state: WorkflowState, runtime: Runtime[WorkflowRuntimeContext]) -> dict[str, Any]:
    service = runtime.context.department_execution_service
    if service is None or not hasattr(service, "execute_it_tool"):
        raise InactiveWorkflowNodeError("IT tool service is unavailable")
    result = await service.execute_it_tool(state)
    execution = state.execution.model_copy(update={
        "tool_results": [*state.execution.tool_results, result],
        "last_operation": result["operation"], "last_operation_status": "completed",
        "department_result": {},
    })
    return {"execution": execution}
