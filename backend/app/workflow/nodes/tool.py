from typing import Any
from langgraph.runtime import Runtime
from app.workflow.state import WorkflowRuntimeContext, WorkflowState
from app.workflow.exceptions import InactiveWorkflowNodeError


async def department_tool_node(state: WorkflowState, runtime: Runtime[WorkflowRuntimeContext]) -> dict[str, Any]:
    service = runtime.context.department_execution_service
    if service is None:
        raise InactiveWorkflowNodeError("Department tool service is unavailable")
    department = state.execution.department_result.get("department_type")
    if department == "it":
        result = await service.execute_it_tool(state)
    elif department == "finance":
        result = await service.execute_finance_tool(state)
    elif department == "procurement":
        result = await service.execute_procurement_tool(state)
    else:
        raise InactiveWorkflowNodeError("Department tool is unavailable")
    execution = state.execution.model_copy(update={
        "tool_results": [*state.execution.tool_results, result],
        "last_operation": result["operation"], "last_operation_status": "completed",
        "department_result": {},
    })
    return {"execution": execution}


it_read_tool_node = department_tool_node
