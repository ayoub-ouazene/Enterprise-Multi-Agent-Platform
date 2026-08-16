"""Department execution step: resolve department agent and run it.

Delegates to existing department agents in ``app/departments/*/agent.py``.  
Expects the agent to return a dict with ``next_action`` field.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionContext
from app.departments.registry import build_default_department_registry
from app.departments.execution import DepartmentExecutionService
from app.requests.enums import RequestStatus
from app.workflow.simple_state import ExecutionStatus, WorkflowState

logger = logging.getLogger(__name__)


class DepartmentStep:
    """Thin wrapper around ``DepartmentExecutionService``."""

    def __init__(self, execution_service: DepartmentExecutionService) -> None:
        self.execution = execution_service

    async def run(self, state: WorkflowState) -> WorkflowState:
        dept_type = state.request.active_department_type
        if dept_type is None:
            logger.error("No active department type set")
            return self._fail(state, "No active department configured")

        # Build execution context from current state
        context = self._build_context(state)

        try:
            raw_result = await self.execution.execute_agent(dept_type, context)
        except Exception as exc:
            logger.exception("Department execution failed: %s", exc)
            return self._fail(state, f"Department execution failed: {exc}")

        return self._apply_result(state, raw_result)

    def _build_context(self, state: WorkflowState) -> DepartmentExecutionContext:
        """Create execution context from current workflow state."""
        return DepartmentExecutionContext(
            request_id=state.request.request_id,
            company_id=state.request.company_id,
            requester_user_id=state.request.requester_user_id,
            requester_employee_id=state.request.requester_employee_id,
            requester_department_id=None,
            requester_actor_type=None,
            requester_is_manager=False,
            owner_department_type=state.request.owner_department_type,
            active_department_type=state.request.active_department_type,
            request_type=state.request.request_type,
            request_summary=state.request.summary,
            current_stage=state.request.current_stage,
            current_plan=state.planning.current_plan,
            completed_steps=list(state.planning.completed_steps),
            pending_steps=list(state.planning.pending_steps),
            latest_user_input=state.routing.latest_answer,
            relevant_custom_data={},
            collaboration_input=None,
            collaboration_result=None,
            review_feedback=None,
            human_response=None,
            tool_results=list(state.execution.tool_results),
            department_data=dict(state.execution.department_data),
        )

    @staticmethod
    def _apply_result(state: WorkflowState, result: dict[str, Any]) -> WorkflowState:
        """Map department result dict to workflow state transitions."""
        next_action = result.get("next_action", "complete_request")
        decision = result.get("decision", "completed")
        reason = result.get("reason", "Department processing completed")
        user_message = result.get("user_message", "Processing completed")

        # Map old action strings to ExecutionStatus
        action_map = {
            "continue_department": ExecutionStatus.RUNNING,
            "execute_tool": ExecutionStatus.NEEDS_TOOL,
            "collaborate": ExecutionStatus.NEEDS_COLLABORATION,
            "request_review": ExecutionStatus.NEEDS_REVIEW,
            "request_human_action": ExecutionStatus.NEEDS_HUMAN,
            "wait_for_user_input": ExecutionStatus.NEEDS_HUMAN,
            "complete_request": ExecutionStatus.COMPLETED,
            "fail_request": ExecutionStatus.FAILED,
        }

        status = action_map.get(next_action, ExecutionStatus.COMPLETED)

        state = state.with_execution(
            status=status,
            department_result=result,
            department_data=result.get("state_updates", {}).get("execution", {}).get("department_data", {}),
        )

        if status == ExecutionStatus.COMPLETED:
            state = state.with_result(
                final_response=user_message,
                decision=decision,
                reason=reason,
            )
            state = state.with_request(
                status=RequestStatus.COMPLETED,
                current_stage="completed",
            )
        elif status == ExecutionStatus.FAILED:
            state = state.with_failure(
                has_failure=True,
                failure_type="department_failure",
                safe_message=user_message,
                terminal=True,
            )
            state = state.with_result(
                final_response=user_message,
                decision="failed",
                reason=reason,
            )
            state = state.with_request(
                status=RequestStatus.FAILED,
                current_stage="failed",
            )
        elif status == ExecutionStatus.NEEDS_HUMAN:
            state = state.with_human_action(
                required=True,
                action_type=result.get("human_action_type", "approval"),
                decision_package=result.get("decision_package", {}),
                status="waiting",
            )
            state = state.with_request(
                status=RequestStatus.WAITING_FOR_HUMAN_ACTION,
                current_stage="waiting_for_human",
            )

        return state

    @staticmethod
    def _fail(state: WorkflowState, reason: str) -> WorkflowState:
        return (
            state.with_failure(
                has_failure=True,
                failure_type="department_failure",
                safe_message=reason,
                terminal=True,
            )
            .with_request(status=RequestStatus.FAILED, current_stage="failed")
            .with_execution(status=ExecutionStatus.FAILED)
        )


async def department_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    from app.core.config import get_settings
    from app.rag.pinecone import PineconeProvider
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.auth.context import AuthenticatedUser

    # These need to be injected properly – for now we create minimal instances
    # The actual service construction should happen in WorkflowService
    settings = get_settings()
    raise NotImplementedError(
        "department_step requires a properly constructed DepartmentExecutionService. "
        "Call through WorkflowService instead."
    )
