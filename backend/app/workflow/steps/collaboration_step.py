"""Collaboration step: execute inter-department calls with explicit allowed routes."""

from __future__ import annotations

import logging
from typing import Any

from app.core.enums import DepartmentType
from app.workflow.simple_state import WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


# Explicitly allowed collaboration routes for Version 1
_ALLOWED_ROUTES: set[tuple[DepartmentType, DepartmentType, str]] = {
    (DepartmentType.CUSTOMER_SUPPORT, DepartmentType.IT, "diagnose_external_technical_issue"),
    (DepartmentType.HR, DepartmentType.IT, "prepare_employee_onboarding_it"),
    (DepartmentType.IT, DepartmentType.FINANCE, "validate_it_purchase_budget"),
    (DepartmentType.IT, DepartmentType.PROCUREMENT, "find_it_asset_suppliers"),
    (DepartmentType.PROCUREMENT, DepartmentType.FINANCE, "validate_procurement_purchase"),
}

_MAX_DEPTH = 3
_MAX_CALLS = 6


class CollaborationStep:
    """Run a collaborating department as a temporary receiver."""

    def __init__(self, executor: Any | None = None) -> None:
        self._executor = executor

    async def run(self, state: WorkflowState) -> WorkflowState:
        collab = state.collaboration
        dept_result = state.execution.department_result
        collab_request = dept_result.get("collaboration_request")

        if collab_request is None:
            logger.warning("Collaboration step called without request")
            return state.with_execution(status=ExecutionStatus.RUNNING)

        sender = state.request.active_department_type
        receiver_name = collab_request.get("receiver_department")
        action = collab_request.get("action")

        if sender is None or receiver_name is None or action is None:
            logger.error("Invalid collaboration request structure")
            return self._fail(state, "Invalid collaboration request")

        try:
            receiver = DepartmentType(receiver_name)
        except ValueError:
            logger.error("Unknown receiver department: %s", receiver_name)
            return self._fail(state, f"Unknown department: {receiver_name}")

        # Validate route
        route = (sender, receiver, action)
        if route not in _ALLOWED_ROUTES:
            logger.error("Disallowed collaboration route: %s", route)
            return self._fail(state, f"Collaboration not allowed: {sender.value} -> {receiver.value}")

        # Check bounds
        if collab.depth >= _MAX_DEPTH:
            return self._fail(state, "Collaboration depth limit exceeded")
        if collab.total_calls >= _MAX_CALLS:
            return self._fail(state, "Collaboration call limit exceeded")

        logger.info(
            "collaboration_start sender=%s receiver=%s action=%s depth=%d calls=%d request_id=%s",
            sender.value, receiver.value, action, collab.depth + 1, collab.total_calls + 1,
            state.request.request_id,
        )

        # Execute collaboration (delegated to executor)
        try:
            if self._executor is not None:
                result = await self._executor(state, collab_request)
            else:
                result = {"status": "no_executor", "result": {}}
        except Exception as exc:
            logger.exception("Collaboration execution failed: %s", exc)
            return self._fail(state, f"Collaboration failed: {exc}")

        # Update collaboration state
        state = state.with_collaboration(
            sender_department=sender,
            receiver_department=receiver,
            action=action,
            result=result,
            is_active=False,
            depth=collab.depth + 1,
            total_calls=collab.total_calls + 1,
        )

        # Return to owner department for re-evaluation
        return state.with_execution(status=ExecutionStatus.RUNNING)

    @staticmethod
    def _fail(state: WorkflowState, reason: str) -> WorkflowState:
        return (
            state.with_execution(status=ExecutionStatus.FAILED)
            .with_failure(
                has_failure=True,
                failure_type="collaboration_failure",
                safe_message=reason,
                terminal=True,
            )
        )


async def collaboration_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    return await CollaborationStep().run(state)
