"""Tests for the reviewer graph node and routing."""

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.core.enums import DepartmentType
from app.departments.contracts import (
    DepartmentExecutionResult,
    DepartmentExecutionStatus,
    DepartmentNextAction,
)
from app.requests.enums import RequestStatus
from app.workflow.review.schemas import ReviewerDecision, ReviewerResult, RecommendedNextAction
from app.workflow.review.service import ReviewService
from app.workflow.nodes.reviewer import reviewer_node
from app.workflow.routing import route_after_reviewer, route_after_department
from app.workflow.state import (
    DEPARTMENT_COMPLETED_STEP,
    DEPARTMENT_STARTED_STEP,
    REVIEW_COMPLETED_STEP,
    ROUTED_STEP,
    WorkflowExecutionState,
    WorkflowPlanningState,
    WorkflowRequestState,
    WorkflowReviewState,
    WorkflowRoutingState,
    WorkflowState,
    WorkflowRuntimeContext,
    apply_state_update,
)


class FakeRuntime:
    """Minimal langgraph Runtime shim for unit tests."""

    def __init__(self, context: WorkflowRuntimeContext) -> None:
        self.context = context


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
            completed_steps=[ROUTED_STEP, DEPARTMENT_STARTED_STEP, DEPARTMENT_COMPLETED_STEP],
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


def _make_state_with_result(base_state, result):
    return apply_state_update(
        base_state,
        {"execution": base_state.execution.model_copy(
            update={"department_result": result.model_dump(mode="json")}
        )},
    )


class TestReviewerNode:
    def test_approved_marks_review_completed(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(
            settings=None,
            _test_policy_override=lambda r: (True, "test"),
        )
        svc.execute_review = AsyncMock(
            return_value=ReviewerResult(
                decision=ReviewerDecision.APPROVED,
                reason="ok",
                severity="low",
                recommended_next_action=RecommendedNextAction.APPROVE_AND_CONTINUE,
                safe_event_title="Approved",
                safe_event_message="Approved",
            )
        )
        runtime = FakeRuntime(
            WorkflowRuntimeContext(
                router_client=None,
                departments={},
                review_service=svc,
            )
        )
        result = asyncio.run(reviewer_node(state, runtime))
        assert REVIEW_COMPLETED_STEP in result["planning"].completed_steps
        assert result["review"].status == "approved"

    def test_revision_required_clears_department_completed(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(
            settings=None,
            _test_policy_override=lambda r: (True, "test"),
        )
        svc.execute_review = AsyncMock(
            return_value=ReviewerResult(
                decision=ReviewerDecision.REVISION_REQUIRED,
                reason="fix",
                severity="medium",
                recommended_next_action=RecommendedNextAction.REVISE_ONCE,
                safe_event_title="Revision",
                safe_event_message="Revision",
            )
        )
        runtime = FakeRuntime(
            WorkflowRuntimeContext(
                router_client=None,
                departments={},
                review_service=svc,
            )
        )
        result = asyncio.run(reviewer_node(state, runtime))
        assert DEPARTMENT_COMPLETED_STEP not in result["planning"].completed_steps
        assert result["planning"].current_step == "reviewer_requested_revision"
        assert result["review"].status == "revision_required"
        assert result["review"].revision_attempt_count == 1

    def test_human_escalation_creates_human_action(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(
            settings=None,
            _test_policy_override=lambda r: (True, "test"),
        )
        svc.execute_review = AsyncMock(
            return_value=ReviewerResult(
                decision=ReviewerDecision.HUMAN_ESCALATION_REQUIRED,
                reason="risky",
                severity="high",
                recommended_next_action=RecommendedNextAction.ESCALATE_TO_HUMAN,
                safe_event_title="Escalated",
                safe_event_message="Escalated",
            )
        )
        runtime = FakeRuntime(
            WorkflowRuntimeContext(
                router_client=None,
                departments={},
                review_service=svc,
            )
        )
        result = asyncio.run(reviewer_node(state, runtime))
        assert result["review"].status == "human_escalation_required"
        assert result["request"].status == RequestStatus.WAITING_FOR_HUMAN_ACTION
        assert result["human_action"].required is True
        assert result["human_action"].status == "pending"

    def test_rejected_routes_to_failure(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        svc = ReviewService(
            settings=None,
            _test_policy_override=lambda r: (True, "test"),
        )
        svc.execute_review = AsyncMock(
            return_value=ReviewerResult(
                decision=ReviewerDecision.REJECTED,
                reason="bad",
                severity="critical",
                recommended_next_action=RecommendedNextAction.REJECT_AND_FAIL,
                safe_event_title="Rejected",
                safe_event_message="Rejected",
            )
        )
        runtime = FakeRuntime(
            WorkflowRuntimeContext(
                router_client=None,
                departments={},
                review_service=svc,
            )
        )
        result = asyncio.run(reviewer_node(state, runtime))
        assert result["review"].status == "rejected"


class TestRouteAfterReviewer:
    def test_approved_complete_request(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {"review": state.review.model_copy(update={"decision": "approved"})},
        )
        route = route_after_reviewer(state)
        assert route == "completion"

    def test_revision_required(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {"review": state.review.model_copy(update={"decision": "revision_required"})},
        )
        route = route_after_reviewer(state)
        assert route == "department_execution"

    def test_human_escalation(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {"review": state.review.model_copy(update={"decision": "human_escalation_required"})},
        )
        route = route_after_reviewer(state)
        assert route == "human_action"

    def test_rejected(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {"review": state.review.model_copy(update={"decision": "rejected"})},
        )
        route = route_after_reviewer(state)
        assert route == "failure"


class TestRouteAfterDepartmentDeterministicReview:
    def test_policy_override_routes_to_reviewer(self, base_state):
        # IT + privileged access keyword triggers review
        result = DepartmentExecutionResult(
            department_type=DepartmentType.IT,
            status=DepartmentExecutionStatus.COMPLETED,
            decision="grant_admin_access",
            reason="User needs admin privileges",
            user_message="Done",
            current_stage="stage_1",
            completed_step="department_execution",
            next_action=DepartmentNextAction.COMPLETE_REQUEST,
            is_terminal=True,
            safe_event_title="Done",
            safe_event_message="Done",
        )
        state = _make_state_with_result(base_state, result)
        route = route_after_department(state)
        assert route == "reviewer"

    def test_no_trigger_routes_to_completion(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        # No high spend, no tools, no human required
        route = route_after_department(state)
        assert route == "completion"

    def test_review_already_completed_skips_reviewer(self, base_state, approved_result):
        state = _make_state_with_result(base_state, approved_result)
        state = apply_state_update(
            state,
            {
                "planning": state.planning.model_copy(
                    update={
                        "completed_steps": [
                            ROUTED_STEP,
                            DEPARTMENT_STARTED_STEP,
                            DEPARTMENT_COMPLETED_STEP,
                            REVIEW_COMPLETED_STEP,
                        ]
                    }
                )
            },
        )
        route = route_after_department(state)
        # When review is already completed, route by result next_action
        assert route == "completion"
