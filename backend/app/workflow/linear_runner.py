"""Minimal linear workflow runner that replaces LangGraph graph execution.

Replaces the complex ``self.graph.astream(..., stream_mode='updates', version='v2')``
with a simple async while-loop that runs steps sequentially.
"""

from __future__ import annotations

import logging
from typing import Any

from app.requests.enums import RequestStatus
from app.workflow.router_output import RouterOutput
from app.workflow.state import WorkflowState, add_completed_step

logger = logging.getLogger(__name__)


async def run_linear(
    state: WorkflowState,
    *,
    execute_router,
    execute_department,
    execute_tool,
    execute_collaboration,
    execute_review,
    execute_human_action,
    execute_completion,
    persist_checkpoint,
    preclassified_output: RouterOutput | None = None,
    precomputed: dict[str, Any] | None = None,
) -> WorkflowState:
    """Run workflow steps in a linear loop until terminal."""
    current = state
    steps = 0
    max_steps = 30

    while not _is_terminal(current) and steps < max_steps:
        steps += 1

        # --- Determine next step ---
        completed = set(current.planning.completed_steps)
        dept_result = current.execution.department_result or {}

        if "router_routed" not in completed and "placeholder_routed" not in completed:
            current = await execute_router(current, preclassified_output)
            preclassified_output = None

        elif "department_execution_started" not in completed and "placeholder_department_started" not in completed:
            current = add_completed_step(current, "department_execution_started")

        elif "department_execution_completed" not in completed and "placeholder_department_completed" not in completed:
            if precomputed is not None:
                current = current.model_copy(
                    update={"execution": current.execution.model_copy(
                        update={"department_result": precomputed})}
                )
                current = add_completed_step(current, "department_execution_completed")
                precomputed = None
            else:
                current = await execute_department(current)
                current = add_completed_step(current, "department_execution_completed")

        elif dept_result.get("requires_tool"):
            current = await execute_tool(current)

        elif dept_result.get("requires_collaboration"):
            current = await execute_collaboration(current)

        elif dept_result.get("requires_review"):
            current = await execute_review(current)

        elif dept_result.get("requires_human_action"):
            current = await execute_human_action(current)

        else:
            current = await execute_completion(current)

        await persist_checkpoint(current)

    if steps >= max_steps:
        logger.error("Workflow hit max step limit")

    return current


def _is_terminal(state: WorkflowState) -> bool:
    return state.request.status in {
        RequestStatus.COMPLETED,
        RequestStatus.FAILED,
        RequestStatus.REJECTED,
        RequestStatus.CANCELLED,
    }
