"""ReviewService: centralized one-revision quality control.

- Deterministic trigger policy (overrides department flag)
- Package assembly from department result
- Reviewer LLM execution via GroqReviewerClient
- Decision routing and one-revision enforcement
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionResult,
    ReviewFeedbackContext,
    DepartmentHumanActionRequest,
)
from app.llm.exceptions import ReviewerProviderError, ReviewerOutputError, ReviewerConfigurationError
from app.workflow.review.policy import should_trigger_review
from app.workflow.review.schemas import (
    DeterministicFact,
    FeedbackItem,
    RecommendedNextAction,
    ReviewPackage,
    ReviewerDecision,
    ReviewerResult,
)
from app.workflow.state import REVIEW_COMPLETED_STEP, WorkflowState


class ReviewService:
    """Centralized review orchestration. Stateless per-request; no tool access."""

    def __init__(
        self,
        settings: Settings,
        *,
        llm_client: Any | None = None,
        _test_policy_override: Any | None = None,
    ) -> None:
        self.settings = settings
        self._llm = llm_client
        self._policy = _test_policy_override or should_trigger_review

    def _resolve_llm(self) -> Any:
        if self._llm is not None:
            return self._llm
        from app.llm.groq import GroqReviewerClient
        return GroqReviewerClient(self.settings)

    def should_trigger_review(self, result: DepartmentExecutionResult) -> tuple[bool, str]:
        """Deterministic policy check. May override the department's own flag."""
        return self._policy(result)

    def build_review_package(
        self,
        state: WorkflowState,
        department_result: DepartmentExecutionResult,
        *,
        review_reason: str,
    ) -> ReviewPackage:
        """Assemble a safe, bounded ReviewPackage from trusted workflow state."""
        facts: list[DeterministicFact] = []
        for tr in state.execution.tool_results[-10:]:
            facts.append(
                DeterministicFact(
                    fact_name=str(tr.get("operation", "unknown_tool")),
                    authoritative_value=str(tr.get("result", tr.get("output", "")))[:500],
                    proposed_value=str(department_result.state_updates.execution.department_data.get("tool_summary", ""))[:500] if department_result.state_updates.execution else None,
                    source_type="tool_result",
                    source_reference=f"tool:{tr.get('operation', 'unknown')}",
                    match_status="unchecked",
                )
            )

        collab_ctx = None
        if state.collaboration.is_active and state.collaboration.active:
            collab_ctx = {
                "collaboration_id": str(state.collaboration.active.collaboration_id),
                "sender": state.collaboration.active.sender_department.value,
                "receiver": state.collaboration.active.receiver_department.value,
                "action": state.collaboration.active.action,
            }

        human_action_summary = None
        if department_result.human_action_request:
            human_action_summary = {
                "action_type": department_result.human_action_request.action_type,
                "assigned_role": (
                    department_result.human_action_request.assigned_role.value
                    if department_result.human_action_request.assigned_role else None
                ),
                "request_summary": department_result.human_action_request.request_summary,
            }

        active_dept = department_result.department_type
        owner_dept = state.routing.selected_department or active_dept

        return ReviewPackage(
            request_id=state.request.request_id,
            company_id=state.request.company_id,
            owner_department=owner_dept,
            active_department=active_dept,
            request_type=state.request.request_type,
            request_summary=state.request.summary,
            department_result=department_result.model_dump(mode="json"),
            proposed_decision=department_result.decision,
            proposed_reason=department_result.reason,
            proposed_user_message=department_result.user_message,
            proposed_next_action=department_result.next_action.value,
            policy_references=state.execution.retrieval_references[:50],
            evidence_references=state.execution.retrieval_references[:50],
            deterministic_facts=facts,
            safe_tool_result_summaries=[
                str(tr.get("summary", tr.get("operation", "")))[:500]
                for tr in state.execution.tool_results[-10:]
            ],
            collaboration_context=collab_ctx,
            human_action_package_summary=human_action_summary,
            risk_flags=department_result.state_updates.execution.department_data.get("risk_flags", [])
            if department_result.state_updates.execution and department_result.state_updates.execution.department_data else [],
            review_reason=review_reason,
            review_attempt=state.review.review_attempt_count,
            revision_attempt=state.review.revision_attempt_count,
        )

    def _apply_revision_cap(self, result: ReviewerResult, state: WorkflowState) -> ReviewerResult:
        """Convert a second revision request into human escalation."""
        if (
            result.decision == ReviewerDecision.REVISION_REQUIRED
            and state.review.revision_attempt_count >= self.settings.workflow_review_max_revisions
        ):
            safe_feedback = list(result.structured_feedback)
            safe_feedback.append(
                FeedbackItem(
                    category="workflow",
                    description="Maximum revision attempts (1) already used.",
                    required_change="Escalate to human review.",
                    severity="high",
                )
            )
            return result.model_copy(
                update={
                    "decision": ReviewerDecision.HUMAN_ESCALATION_REQUIRED,
                    "reason": f"{result.reason} Maximum revision limit reached; escalating to human.",
                    "recommended_next_action": RecommendedNextAction.ESCALATE_TO_HUMAN,
                    "structured_feedback": safe_feedback,
                    "safe_event_title": "Review escalated to human",
                    "safe_event_message": "The Reviewer required changes but the revision limit was reached.",
                }
            )
        return result

    async def execute_review(
        self,
        state: WorkflowState,
    ) -> ReviewerResult:
        """Run the Reviewer LLM and return a structured decision."""
        result = DepartmentExecutionResult.model_validate(state.execution.department_result)
        should_review, review_reason = self.should_trigger_review(result)
        if not should_review:
            return ReviewerResult(
                decision=ReviewerDecision.APPROVED,
                reason="Deterministic policy determined review is unnecessary.",
                severity="low",
                safe_event_title="Review bypassed",
                safe_event_message=f"Low-risk result bypassed review: {review_reason}",
                recommended_next_action=RecommendedNextAction.APPROVE_AND_CONTINUE,
            )

        package = self.build_review_package(state, result, review_reason=review_reason)
        llm = self._resolve_llm()
        try:
            reviewer_result = await llm.review(package)
        except (ReviewerProviderError, ReviewerOutputError, ReviewerConfigurationError) as exc:
            safe_reason = str(exc) if str(exc) else "Reviewer unavailable"
            return ReviewerResult(
                decision=ReviewerDecision.HUMAN_ESCALATION_REQUIRED,
                reason=f"Reviewer failure: {safe_reason}",
                severity="high",
                safe_event_title="Reviewer failure",
                safe_event_message="The Reviewer could not complete its check. Escalating to human.",
                recommended_next_action=RecommendedNextAction.ESCALATE_TO_HUMAN,
            )

        # Post-process: resolve contradictions and enforce revision cap
        if reviewer_result.decision == ReviewerDecision.APPROVED and reviewer_result.safety_status.value in ("unsafe", "unchecked") and reviewer_result.severity in ("high", "critical"):
            reviewer_result = reviewer_result.model_copy(
                update={
                    "decision": ReviewerDecision.HUMAN_ESCALATION_REQUIRED,
                    "reason": f"{reviewer_result.reason} Approved but safety/status is concerning; escalating.",
                    "recommended_next_action": RecommendedNextAction.ESCALATE_TO_HUMAN,
                }
            )

        reviewer_result = self._apply_revision_cap(reviewer_result, state)
        return reviewer_result

    def apply_decision(self, state: WorkflowState, result: ReviewerResult) -> dict[str, Any]:
        """Produce a state-update dict from a ReviewerResult."""
        now = datetime.now(UTC)
        update: dict[str, Any] = {
            "review": state.review.model_copy(
                update={
                    "required": True,
                    "status": result.decision.value,
                    "decision": result.decision.value,
                    "review_reason": state.review.review_reason or "deterministic_policy",
                    "reviewed_at": now,
                    "package_summary": {
                        "decision": result.decision.value,
                        "reason": result.reason,
                        "severity": result.severity,
                    },
                    "feedback": [item.model_dump(mode="json") for item in result.structured_feedback],
                    "required_changes": result.required_changes,
                    "review_attempt_count": state.review.review_attempt_count + 1,
                    "final_review_completed": result.decision != ReviewerDecision.REVISION_REQUIRED,
                }
            ),
        }

        if result.decision == ReviewerDecision.REVISION_REQUIRED:
            update["review"] = update["review"].model_copy(
                update={
                    "revision_attempt_count": state.review.revision_attempt_count + 1,
                }
            )

        elif result.decision == ReviewerDecision.APPROVED:
            update["review"] = update["review"].model_copy(
                update={
                    "revision_completed": state.review.revision_attempt_count > 0,
                }
            )

        elif result.decision == ReviewerDecision.HUMAN_ESCALATION_REQUIRED:
            update["review"] = update["review"].model_copy(
                update={
                    "human_action_id": uuid4(),
                }
            )

        return update

    def prepare_revision_feedback(self, state: WorkflowState) -> ReviewFeedbackContext:
        """Build the feedback context passed to the department on revision."""
        feedback_items = state.review.feedback
        if not feedback_items:
            return ReviewFeedbackContext(
                status="revision_required",
                feedback="Please review and improve the result.",
                reason="The Reviewer requested changes.",
            )
        combined = "; ".join(
            f"[{item.get('category', 'general')}] {item.get('description', '')}"
            for item in feedback_items
        )
        return ReviewFeedbackContext(
            status="revision_required",
            feedback=combined[:2000],
            reason=state.review.package_summary.get("reason", "The Reviewer requested changes."),
        )

    def prepare_human_action_from_review(
        self,
        state: WorkflowState,
        result: DepartmentExecutionResult,
    ) -> DepartmentHumanActionRequest:
        """Enrich a human action package using reviewer findings."""
        original = result.human_action_request
        if original is None:
            from app.core.enums import ActorType
            original = DepartmentHumanActionRequest(
                action_type="reviewer_escalation",
                assigned_role=ActorType.DEPARTMENT_MANAGER,
                request_summary=state.request.summary,
                evidence_summary="The Reviewer escalated this request.",
                recommendation="Please review the department result independently.",
                exact_action_required="Review the proposed decision and confirm or reject.",
                reason=state.review.package_summary.get("reason", "Reviewer escalation."),
            )

        enriched_reason = original.reason
        if state.review.package_summary:
            enriched_reason = f"{enriched_reason} | Reviewer: {state.review.package_summary.get('reason', '')}"

        feedback_notes = ""
        for item in state.review.feedback:
            fb = f"[{item.get('category', '')}] {item.get('description', '')}"
            feedback_notes += fb + "; "

        evidence = original.evidence_summary
        if feedback_notes:
            evidence = f"{evidence} | Reviewer feedback: {feedback_notes[:1000]}"

        return original.model_copy(
            update={
                "reason": enriched_reason[:2000],
                "evidence_summary": evidence[:2000],
            }
        )

    def build_review_completed_state(self, state: WorkflowState) -> dict[str, Any]:
        """Mark review as done so routing can proceed."""
        planning = state.planning.model_copy(
            update={
                "completed_steps": state.planning.completed_steps + [REVIEW_COMPLETED_STEP],
            }
        )
        return {"planning": planning}
