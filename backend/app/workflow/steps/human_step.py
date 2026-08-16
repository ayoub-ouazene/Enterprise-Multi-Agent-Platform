"""Human action step: pause the workflow waiting for human input."""

from __future__ import annotations

import logging

from app.requests.enums import RequestStatus
from app.workflow.simple_state import WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


class HumanActionStep:
    """Pause the workflow for human approval or action."""

    async def run(self, state: WorkflowState) -> WorkflowState:
        logger.info(
            "human_action_pause request_id=%s action_type=%s",
            state.request.request_id,
            state.human_action.action_type,
        )

        # Mark request as waiting
        state = state.with_request(
            status=RequestStatus.WAITING_FOR_HUMAN_ACTION,
            current_stage="waiting_for_human",
        )

        # If we already have a human response (resume flow), process it
        if state.human_action.response:
            return self._process_response(state)

        return state

    @staticmethod
    def _process_response(state: WorkflowState) -> WorkflowState:
        """Resume after receiving human response."""
        response = state.human_action.response
        decision = response.get("decision", "approved")

        if decision == "approved":
            return state.with_execution(status=ExecutionStatus.RUNNING)
        if decision in {"rejected", "denied"}:
            return (
                state.with_execution(status=ExecutionStatus.COMPLETED)
                .with_request(status=RequestStatus.REJECTED, current_stage="rejected")
            )
        # Default: continue to department for re-evaluation
        return state.with_execution(status=ExecutionStatus.RUNNING)


async def human_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    return await HumanActionStep().run(state)
