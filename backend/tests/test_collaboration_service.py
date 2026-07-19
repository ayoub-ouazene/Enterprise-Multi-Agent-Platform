import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.requests.enums import RequestStatus
from app.workflow.collaboration.enums import CollaborationRuntimeStatus
from app.workflow.collaboration.exceptions import (
    CollaborationLimitError,
    CollaborationRouteError,
    CollaborationValidationError,
)
from app.workflow.collaboration.schemas import CollaborationReceiverOutcome
from app.workflow.collaboration.service import CollaborationService
from app.workflow.state import (
    DepartmentRuntimeContext,
    WorkflowRequestState,
    WorkflowState,
    apply_state_update,
)


class Executor:
    def __init__(self) -> None:
        self.calls = 0

    async def execute_collaboration_receiver(self, state, request):
        self.calls += 1
        return CollaborationReceiverOutcome(
            reason="A safe diagnosis was returned.",
            result={
                "diagnosis_status": "diagnosed",
                "diagnosis_category": "configuration",
                "additional_troubleshooting": [],
                "technician_action_required": False,
                "internal_resolution_summary": "A safe configuration issue was identified.",
                "safe_customer_support_response": "Please retry the documented steps.",
                "confidence": "high",
                "unresolved_reason": None,
            },
        )


def settings(**updates):
    values = {
        "workflow_max_collaboration_depth": 3,
        "workflow_max_collaboration_calls": 6,
        "workflow_max_collaboration_attempts": 2,
    }
    values.update(updates)
    return SimpleNamespace(**values)


def initial_state():
    owner_id, it_id = uuid4(), uuid4()
    state = WorkflowState(
        request=WorkflowRequestState(
            request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
            owner_department_id=owner_id, active_department_id=owner_id,
            request_type="technical_issue", summary="Portal unavailable",
            status=RequestStatus.PROCESSING, current_stage="customer_support_processing",
        )
    )
    state.collaboration.request = {
        "request_id": str(state.request.request_id),
        "sender_department": "customer_support",
        "receiver_department": "it",
        "action": "diagnose_external_technical_issue",
        "payload": {"issue_summary": "Portal unavailable"},
        "expected_output": {},
    }
    departments = {
        DepartmentType.CUSTOMER_SUPPORT: DepartmentRuntimeContext(owner_id, True),
        DepartmentType.IT: DepartmentRuntimeContext(it_id, True),
    }
    return state, departments


def test_start_execute_return_preserves_owner_and_restores_active_department() -> None:
    state, departments = initial_state()
    owner_id = state.request.owner_department_id
    executor = Executor()
    service = CollaborationService(settings(), executor)
    state = apply_state_update(state, service.prepare(state, departments))
    assert state.request.owner_department_id == owner_id
    assert state.request.active_department_id == departments[DepartmentType.IT].department_id
    assert state.collaboration.active.status == CollaborationRuntimeStatus.PENDING
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    state = apply_state_update(state, service.finish(state, departments))
    assert state.request.owner_department_id == owner_id
    assert state.request.active_department_id == owner_id
    assert state.collaboration.active is None
    assert len(state.collaboration.history) == 1
    assert executor.calls == 1


def test_completed_identical_collaboration_replays_without_receiver_execution() -> None:
    state, departments = initial_state()
    request = dict(state.collaboration.request)
    executor = Executor()
    service = CollaborationService(settings(), executor)
    state = apply_state_update(state, service.prepare(state, departments))
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    state = apply_state_update(state, service.finish(state, departments))
    state.collaboration.request = request
    state = apply_state_update(state, service.prepare(state, departments))
    assert state.collaboration.active.status == CollaborationRuntimeStatus.COMPLETED
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    state = apply_state_update(state, service.finish(state, departments))
    assert executor.calls == 1
    assert len(state.collaboration.history) == 1


def test_unapproved_route_wrong_request_and_call_limit_are_rejected() -> None:
    state, departments = initial_state()
    service = CollaborationService(settings(), Executor())
    state.collaboration.request["receiver_department"] = "finance"
    with pytest.raises(CollaborationRouteError):
        service.prepare(state, departments)
    state, departments = initial_state()
    state.collaboration.request["request_id"] = str(uuid4())
    with pytest.raises(CollaborationValidationError):
        service.prepare(state, departments)
    state, departments = initial_state()
    state.collaboration.total_call_count = 6
    with pytest.raises(CollaborationLimitError):
        service.prepare(state, departments)


def test_nested_procurement_finance_flow_uses_same_request_and_return_stack() -> None:
    owner_id, procurement_id, finance_id = uuid4(), uuid4(), uuid4()
    state = WorkflowState(request=WorkflowRequestState(
        request_id=uuid4(), company_id=uuid4(), requester_user_id=uuid4(),
        owner_department_id=owner_id, active_department_id=owner_id,
        request_type="hardware_request", summary="Find laptops",
        status=RequestStatus.PROCESSING, current_stage="it_processing",
    ))
    state.collaboration.request = {
        "request_id": str(state.request.request_id), "sender_department": "it",
        "receiver_department": "procurement", "action": "find_it_asset_suppliers",
        "payload": {"asset_or_software": "Laptop", "currency": "USD"},
        "expected_output": {},
    }
    departments = {
        DepartmentType.IT: DepartmentRuntimeContext(owner_id, True),
        DepartmentType.PROCUREMENT: DepartmentRuntimeContext(procurement_id, True),
        DepartmentType.FINANCE: DepartmentRuntimeContext(finance_id, True),
    }

    class NestedExecutor:
        procurement_calls = 0

        async def execute_collaboration_receiver(self, current_state, request):
            if request.action == "find_it_asset_suppliers":
                self.procurement_calls += 1
                if self.procurement_calls == 1:
                    from app.departments.contracts import DepartmentCollaborationRequest
                    return CollaborationReceiverOutcome(
                        reason="Finance validation required.",
                        nested_request=DepartmentCollaborationRequest(
                            request_id=request.request_id,
                            sender_department=DepartmentType.PROCUREMENT,
                            receiver_department=DepartmentType.FINANCE,
                            action="validate_procurement_purchase",
                            payload={
                                "candidate_reference": "supplier-1",
                                "total_amount": "1000.00", "currency": "USD",
                                "business_reason": "Laptop purchase",
                            }, expected_output={},
                        ),
                    )
                return CollaborationReceiverOutcome(
                    reason="Shortlist ready.",
                    result={
                        "eligible_candidate_count": 1, "shortlist": [],
                        "recommendation": None, "estimated_total_costs": [],
                        "finance_revalidation_required": False,
                        "reason": "Shortlist ready.", "required_next_action": None,
                    },
                )
            return CollaborationReceiverOutcome(
                reason="Budget validated.",
                result={
                    "finance_decision": "validated", "validated_amount": "1000.00",
                    "currency": "USD", "budget_sufficient": True,
                    "approval_required": False, "reservation_reference": None,
                    "commitment_reference": None, "reason": "Budget validated.",
                    "required_next_action": None,
                },
            )

    executor = NestedExecutor()
    service = CollaborationService(settings(), executor)
    state = apply_state_update(state, service.prepare(state, departments))
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    assert state.collaboration.request["action"] == "validate_procurement_purchase"
    state = apply_state_update(state, service.prepare(state, departments))
    assert len(state.collaboration.return_stack) == 1
    assert state.collaboration.active.depth == 2
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    state = apply_state_update(state, service.finish(state, departments))
    assert state.collaboration.active.action == "find_it_asset_suppliers"
    assert state.request.active_department_id == procurement_id
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    state = apply_state_update(state, service.finish(state, departments))
    assert state.request.active_department_id == owner_id
    assert state.request.owner_department_id == owner_id
    assert state.collaboration.total_call_count == 2
    assert [item.action for item in state.collaboration.history] == [
        "validate_procurement_purchase", "find_it_asset_suppliers"
    ]


def test_invalid_receiver_result_fails_safely_and_returns_to_sender() -> None:
    state, departments = initial_state()

    class InvalidExecutor:
        async def execute_collaboration_receiver(self, state, request):
            return CollaborationReceiverOutcome(
                reason="Invalid result.", result={"untrusted": "value"}
            )

    service = CollaborationService(settings(), InvalidExecutor())
    state = apply_state_update(state, service.prepare(state, departments))
    state = apply_state_update(state, asyncio.run(service.execute(state)))
    assert state.collaboration.active.status == CollaborationRuntimeStatus.FAILED
    assert "invalid result" in state.collaboration.active.error_safe.lower()
    state = apply_state_update(state, service.finish(state, departments))
    assert state.request.active_department_id == state.request.owner_department_id
    assert state.collaboration.history[-1].status == CollaborationRuntimeStatus.FAILED
