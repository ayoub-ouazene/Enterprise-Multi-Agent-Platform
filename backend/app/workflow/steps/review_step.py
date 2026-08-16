"""Reviewer step: independent quality review of department decisions."""

from __future__ import annotations

import logging
from typing import Any

from app.llm.client import GroqLLMClient
from app.workflow.prompts.reviewer import REVIEWER_SYSTEM_PROMPT, build_reviewer_user_message
from app.workflow.simple_state import WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


class ReviewStep:
    """Run the reviewer model once and update state with feedback."""

    def __init__(self, llm_client: GroqLLMClient) -> None:
        self.llm = llm_client

    async def run(self, state: WorkflowState) -> WorkflowState:
        review_count = state.review.revision_count
        if review_count >= 1:
            logger.info("Review already performed once; skipping")
            return state.with_execution(status=ExecutionStatus.RUNNING)

        # Build review package from current state
        package = self._build_package(state)

        try:
            raw = await self.llm.generate(
                messages=[
                    {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                    {"role": "user", "content": build_reviewer_user_message(package)},
                ],
                model=self.llm.settings.groq_model_reviewer,
                role_name="reviewer",
            )
        except Exception as exc:
            logger.exception("Reviewer failed: %s", exc)
            # Fail open: continue without review
            return state.with_execution(status=ExecutionStatus.RUNNING)

        decision = raw.get("decision", "approved")
        logger.info(
            "reviewer_decision decision=%s request_id=%s",
            decision,
            state.request.request_id,
        )

        state = state.with_review(
            required=True,
            status=decision,
            feedback=raw.get("feedback"),
            decision=decision,
            revision_count=review_count + 1,
        )

        if decision == "approved":
            return state.with_execution(status=ExecutionStatus.RUNNING)
        if decision == "revision_required":
            return state.with_execution(status=ExecutionStatus.RUNNING)
        if decision == "human_escalation_required":
            return (
                state.with_execution(status=ExecutionStatus.NEEDS_HUMAN)
                .with_human_action(
                    required=True,
                    action_type="reviewer_escalation",
                    decision_package=package,
                    status="waiting",
                )
            )
        if decision == "rejected":
            return state.with_execution(status=ExecutionStatus.FAILED)

        return state.with_execution(status=ExecutionStatus.RUNNING)

    @staticmethod
    def _build_package(state: WorkflowState) -> dict[str, Any]:
        """Build the review package from current workflow state."""
        return {
            "request_id": str(state.request.request_id),
            "request_type": state.request.request_type,
            "department": state.request.active_department_type.value if state.request.active_department_type else None,
            "decision": state.execution.department_result.get("decision"),
            "reason": state.execution.department_result.get("reason"),
            "user_message": state.execution.department_result.get("user_message"),
            "tool_results": state.execution.tool_results,
        }


async def review_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    from app.core.config import get_settings
    settings = get_settings()
    client = GroqLLMClient(settings)
    return await ReviewStep(client).run(state)
