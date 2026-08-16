"""Completion step: finalize a terminal workflow state."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.requests.enums import RequestStatus
from app.workflow.simple_state import WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


async def completion_step(state: WorkflowState) -> WorkflowState:
    """Mark the request as completed and set final fields."""
    response = state.result.final_response or "The request has been completed."
    state = (
        state.with_request(
            status=RequestStatus.COMPLETED,
            current_stage="completed",
        )
        .with_execution(status=ExecutionStatus.COMPLETED)
        .with_result(
            final_response=response,
            decision=state.result.decision or "completed",
            reason=state.result.reason or "Workflow completed",
            completed_at=datetime.now(timezone.utc),
        )
    )
    logger.info(
        "workflow_complete request_id=%s decision=%s",
        state.request.request_id,
        state.result.decision,
    )
    return state
