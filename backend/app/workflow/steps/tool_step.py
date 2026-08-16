"""Tool executor step: run department-approved tools deterministically."""

from __future__ import annotations

import logging
from typing import Any

from app.workflow.simple_state import WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


class ToolStep:
    """Execute a tool requested by the department agent."""

    def __init__(self, executor: Any | None = None) -> None:
        """``executor`` receives (state, tool_request) and returns result dict."""
        self._executor = executor

    async def run(self, state: WorkflowState) -> WorkflowState:
        dept_result = state.execution.department_result
        tool_request = dept_result.get("tool_request")

        if tool_request is None:
            logger.warning("Tool step called without tool_request; returning to department")
            return state.with_execution(status=ExecutionStatus.RUNNING)

        tool_name = tool_request.get("operation", "unknown")
        logger.info(
            "tool_execute operation=%s request_id=%s",
            tool_name,
            state.request.request_id,
        )

        try:
            if self._executor is not None:
                result = await self._executor(state, tool_request)
            else:
                result = {"operation": tool_name, "result": "no_executor", "status": "skipped"}
        except Exception as exc:
            logger.exception("Tool execution failed: %s", exc)
            result = {
                "operation": tool_name,
                "error": str(exc),
                "status": "failed",
            }

        # Append result to tool_results and return to department
        tool_results = list(state.execution.tool_results)
        tool_results.append(result)

        return state.with_execution(
            status=ExecutionStatus.RUNNING,
            tool_results=tool_results,
            last_operation=tool_name,
        )


async def tool_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    # WorkflowService injects a real executor; fallback is no-op
    return await ToolStep().run(state)
