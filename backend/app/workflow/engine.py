"""Linear workflow engine: runs steps in order, checkpointing after each.

This replaces the LangGraph graph (`graph.py`, `nodes/`, `routing.py`)
with an explicit while-loop of typed asynchronous steps.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.workflow.simple_state import WorkflowState

logger = logging.getLogger(__name__)

Step = Callable[[WorkflowState], Awaitable[WorkflowState]]


class LinearEngine:
    """Run workflow steps sequentially, checkpointing after each."""

    def __init__(
        self,
        *,
        router_step: Step,
        department_step: Step,
        tool_step: Step,
        review_step: Step,
        collaboration_step: Step,
        human_step: Step,
        completion_step: Step,
        checkpoint: Callable[[WorkflowState], Awaitable[None]],
        on_error: Callable[[WorkflowState, Exception], Awaitable[WorkflowState]] | None = None,
    ) -> None:
        self.router_step = router_step
        self.department_step = department_step
        self.tool_step = tool_step
        self.review_step = review_step
        self.collaboration_step = collaboration_step
        self.human_step = human_step
        self.completion_step = completion_step
        self.checkpoint = checkpoint
        self.on_error = on_error

    async def run(self, state: WorkflowState) -> WorkflowState:
        """Execute the workflow until terminal."""
        iteration = 0
        max_iterations = 50  # safety guard rail

        while not self._is_terminal(state):
            iteration += 1
            if iteration > max_iterations:
                logger.error("Workflow exceeded max iterations (%d)", max_iterations)
                return self._force_fail(state, "Workflow iteration limit exceeded")

            try:
                state = await self._step(state)
                await self.checkpoint(state)
            except Exception as exc:
                logger.exception("Workflow step failed: %s", exc)
                if self.on_error is not None:
                    state = await self.on_error(state, exc)
                else:
                    state = self._force_fail(state, "Internal workflow error")
                await self.checkpoint(state)

        return state

    async def _step(self, state: WorkflowState) -> WorkflowState:
        """Dispatch to the next logical step based on current state."""
        from app.workflow.simple_state import RoutingStatus, ExecutionStatus

        # 1. Router
        if state.routing.status == RoutingStatus.PENDING:
            logger.info("workflow_step=router request_id=%s", state.request.request_id)
            return await self.router_step(state)

        # 2. Department execution
        if state.execution.status in {
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
        }:
            logger.info("workflow_step=department request_id=%s", state.request.request_id)
            return await self.department_step(state)

        # 3. Tool execution (must come before review/human/completion)
        if state.execution.status == ExecutionStatus.NEEDS_TOOL:
            logger.info("workflow_step=tool request_id=%s", state.request.request_id)
            return await self.tool_step(state)

        # 4. Reviewer
        if state.execution.status == ExecutionStatus.NEEDS_REVIEW:
            logger.info("workflow_step=review request_id=%s", state.request.request_id)
            return await self.review_step(state)

        # 5. Collaboration
        if state.execution.status == ExecutionStatus.NEEDS_COLLABORATION:
            logger.info("workflow_step=collaboration request_id=%s", state.request.request_id)
            return await self.collaboration_step(state)

        # 6. Human action
        if state.execution.status == ExecutionStatus.NEEDS_HUMAN:
            logger.info("workflow_step=human request_id=%s", state.request.request_id)
            return await self.human_step(state)

        # 7. Completion
        if state.execution.status == ExecutionStatus.COMPLETED:
            logger.info("workflow_step=completion request_id=%s", state.request.request_id)
            return await self.completion_step(state)

        # Unknown state – fail safely
        logger.warning(
            "workflow_step=unknown execution_status=%s request_id=%s",
            state.execution.status,
            state.request.request_id,
        )
        return self._force_fail(state, f"Unknown execution status: {state.execution.status}")

    @staticmethod
    def _is_terminal(state: WorkflowState) -> bool:
        from app.requests.enums import RequestStatus

        return state.request.status in {
            RequestStatus.COMPLETED,
            RequestStatus.FAILED,
            RequestStatus.REJECTED,
            RequestStatus.CANCELLED,
        }

    @staticmethod
    def _force_fail(state: WorkflowState, reason: str) -> WorkflowState:
        from app.requests.enums import RequestStatus
        from app.workflow.simple_state import ExecutionStatus, FailureSection

        return (
            state.with_request(status=RequestStatus.FAILED, current_stage="failed")
            .with_execution(status=ExecutionStatus.FAILED)
            .with_failure(
                has_failure=True,
                failure_type="workflow_failure",
                safe_message=reason,
                terminal=True,
            )
        )
