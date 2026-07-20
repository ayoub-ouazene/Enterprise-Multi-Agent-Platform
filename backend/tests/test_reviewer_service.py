"""Tests for the centralized Reviewer service and routing logic."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentHumanActionRequest,
    DepartmentNextAction,
    DepartmentStateUpdates,
)
from app.workflow.review.schemas import (
    FeedbackItem,
    RecommendedNextAction,
    ReviewerDecision,
    ReviewerResult,
)
from app.workflow.review.service import ReviewService
from app.workflow.state import (
    DEPARTMENT_COMPLETED_STEP,
    REVIEW_COMPLETED_STEP,
    WorkflowExecutionState,
    WorkflowPlanningState,
    WorkflowRequestState,
    WorkflowReviewState,
    WorkflowRoutingState,
    WorkflowState,
    apply_state_update,
)


@pytest.fixture
def base_state():
    req_id = uuid4()
    company_id = uuid4()
    dept_id = uuid4()
    return WorkflowState(
        request=WorkflowRequestState(
            request_id=req_id,
            company_id=company_id,
            requester_user_id=uuid4(),
            request_type="test_request",
            owner_department_id=dept_id,
            active_department_id=dept_id,
            summary="test summary",
            current_stage="stage_1",
        ),
        planning=WorkflowPlanningState(
            completed_steps=[DEPARTMENT_COMPLETED_STEP],
            current_step="department_execution",
        ),
        execution=WorkflowExecutionState(
            department_result={},
            tool_results=[],
            retrieval_references=[],
        ),
        routing=WorkflowRoutingState(
            selected_department=DepartmentType.IT,
        ),
    )


@pytest.fixture
def approved_result():
    return DepartmentExecutionResult(
        department_type=DepartmentType.IT,
        status=DepartmentExecutionStatus.COMPLETED,
        decision="approved",
        reason="All good",
        user_message="Done",
        current_stage="stage_1",
        completed_step="department_execution",
        next_action=DepartmentNextAction.COMPLETE_REQUEST,
        is_terminal=True,
        safe_event_title="Done",
        safe_event_message="Done",
    )


@pytest.fixture
def risky_result():
    return DepartmentExecutionResult(
        department_type=DepartmentType.IT,
        status=DepartmentExecutionStatus.COMPLETED,
        decision="approved",
        reason="High spend",
        user_message="Done",
        current_stage="stage_1",
        completed_step="department_execution",
        next_action=DepartmentNextAction.COMPLETE_REQUEST,
        is_terminal=True,
        safe_event_title="Done",
        safe_event_message="Done",
        state_updates=DepartmentStateUpdates(
            execution=None,
        ),
    )


@pytest.fixture
def settings():
    return Settings(
        GROQ_API_KEY="test-key",
        groq_model_reviewer="llama-3.3-70b-versatile",
    )


def _make_state_with_result(base_state, result):
    state = apply_state_update(
        base_state,
        {"execution": base_state.execution.model_copy(
            update={"department_result": result.model_dump(mode="json")}
        )},
    )
    return state


class TestShouldTriggerReview:
    def test_no_tool_results_no_human_no_high_spend_bypasses(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(settings, _test_policy_override=lambda r: (False, "low risk"))
        result = asyncio.run(svc.execute_review(state))
        assert result.decision == ReviewerDecision.APPROVED

    def test_policy_returns_true_triggers_review(self, base_state, approved_result, settings):
        svc = ReviewService(settings, _test_policy_override=lambda r: (True, "policy says so"))
        should, reason = svc.should_trigger_review(approved_result)
        assert should is True
        assert reason == "policy says so"


class TestApplyDecision:
    def test_approved(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(settings)
        reviewer = ReviewerResult(
            decision=ReviewerDecision.APPROVED,
            reason="Looks good",
            severity="low",
            recommended_next_action=RecommendedNextAction.APPROVE_AND_CONTINUE,
            safe_event_title="Approved",
            safe_event_message="Approved",
        )
        update = svc.apply_decision(state, reviewer)
        assert update["review"].status == "approved"
        assert update["review"].review_attempt_count == 1
        assert update["review"].final_review_completed is True

    def test_revision_required(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(settings)
        reviewer = ReviewerResult(
            decision=ReviewerDecision.REVISION_REQUIRED,
            reason="Fix X",
            severity="medium",
            recommended_next_action=RecommendedNextAction.REVISE_ONCE,
            safe_event_title="Revision",
            safe_event_message="Revision",
            structured_feedback=[
                FeedbackItem(
                    category="policy",
                    description="Missing item",
                    required_change="Add item",
                )
            ],
        )
        update = svc.apply_decision(state, reviewer)
        assert update["review"].status == "revision_required"
        assert update["review"].revision_attempt_count == 1
        assert update["review"].final_review_completed is False
        assert len(update["review"].feedback) == 1

    def test_human_escalation(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(settings)
        reviewer = ReviewerResult(
            decision=ReviewerDecision.HUMAN_ESCALATION_REQUIRED,
            reason="Too risky",
            severity="high",
            recommended_next_action=RecommendedNextAction.ESCALATE_TO_HUMAN,
            safe_event_title="Escalated",
            safe_event_message="Escalated",
        )
        update = svc.apply_decision(state, reviewer)
        assert update["review"].status == "human_escalation_required"
        assert update["review"].human_action_id is not None

    def test_revision_cap_second_revision_becomes_escalation(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {"review": state.review.model_copy(update={"revision_attempt_count": 1})},
        )
        svc = ReviewService(settings)
        reviewer = ReviewerResult(
            decision=ReviewerDecision.REVISION_REQUIRED,
            reason="Still wrong",
            severity="high",
            recommended_next_action=RecommendedNextAction.REVISE_ONCE,
            safe_event_title="Revision",
            safe_event_message="Revision",
        )
        capped = svc._apply_revision_cap(reviewer, state)
        assert capped.decision == ReviewerDecision.HUMAN_ESCALATION_REQUIRED


class TestPrepareRevisionFeedback:
    def test_combines_feedback_items(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {
                "review": state.review.model_copy(
                    update={
                        "feedback": [
                            {"category": "policy", "description": "Need policy ref"},
                            {"category": "calculation", "description": "Math off"},
                        ],
                        "package_summary": {"reason": "Fix both"},
                    }
                )
            },
        )
        svc = ReviewService(settings)
        ctx = svc.prepare_revision_feedback(state)
        assert "policy" in ctx.feedback
        assert "calculation" in ctx.feedback
        assert ctx.status == "revision_required"


class TestPrepareHumanActionFromReview:
    def test_enriches_existing_request(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {
                "review": state.review.model_copy(
                    update={
                        "package_summary": {"reason": "Reviewer found issue"},
                        "feedback": [{"category": "policy", "description": "Missing ref"}],
                    }
                )
            },
        )
        svc = ReviewService(settings)
        original = DepartmentHumanActionRequest(
            action_type="approval",
            request_summary="summary",
            evidence_summary="evidence",
            recommendation="approve",
            exact_action_required="sign",
            reason="original reason",
            assigned_role=None,
            assigned_user_id=uuid4(),
        )
        result = approved_result.model_copy(update={"human_action_request": original})
        enriched = svc.prepare_human_action_from_review(state, result)
        assert "Reviewer found issue" in enriched.reason
        assert "policy" in enriched.evidence_summary

    def test_creates_request_when_none_exists(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {
                "review": state.review.model_copy(
                    update={"package_summary": {"reason": "Reviewer found issue"}}
                )
            },
        )
        svc = ReviewService(settings)
        enriched = svc.prepare_human_action_from_review(state, approved_result)
        assert enriched.action_type == "reviewer_escalation"


class TestRevisionLoopPlanClearing:
    def test_node_clears_department_completed_on_revision(self, base_state, approved_result, settings):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {
                "planning": state.planning.model_copy(
                    update={"completed_steps": [DEPARTMENT_COMPLETED_STEP]}
                )
            },
        )
        svc = ReviewService(settings)
        reviewer = ReviewerResult(
            decision=ReviewerDecision.REVISION_REQUIRED,
            reason="Fix",
            severity="medium",
            recommended_next_action=RecommendedNextAction.REVISE_ONCE,
            safe_event_title="Revision",
            safe_event_message="Revision",
        )
        update = svc.apply_decision(state, reviewer)
        assert "planning" not in update


class TestReviewerEventSchema:
    def test_safe_event_fields(self):
        r = ReviewerResult(
            decision=ReviewerDecision.APPROVED,
            reason="ok",
            safe_event_title="Title",
            safe_event_message="Message",
        )
        assert r.safe_event_title == "Title"
        assert r.safe_event_message == "Message"
