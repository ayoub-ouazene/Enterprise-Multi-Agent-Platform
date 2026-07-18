import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.enums import DepartmentType
from app.llm.exceptions import RouterOutputError
from app.requests.enums import RequestStatus
from app.workflow.exceptions import (
    RouterDepartmentUnavailableError,
    RouterOwnerConflictError,
)
from app.workflow.nodes.router import router_node
from app.workflow.router_output import RouterOutput
from app.workflow.state import (
    DepartmentRuntimeContext,
    WorkflowRuntimeContext,
    WorkflowState,
    apply_state_update,
    build_initial_workflow_state,
)


def state() -> WorkflowState:
    return build_initial_workflow_state(
        SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            requester_user_id=uuid4(),
            requester_employee_id=None,
            request_type="routing_pending",
            owner_department_id=None,
            active_department_id=None,
            status=RequestStatus.ROUTING,
            current_stage="routing",
            summary="I need help with my account.",
        )
    )


def routed(department: DepartmentType = DepartmentType.IT) -> RouterOutput:
    return RouterOutput(
        message_category="business_request",
        owner_department=department,
        confidence="high",
        needs_clarification=False,
        clarification_question=None,
        platform_answer=None,
        request_type="account_access_request",
        short_summary="Employee needs account access help.",
        routing_reason="Employee account access belongs to IT.",
        unsupported_reason=None,
        is_capability_gap=False,
    )


def unclear() -> RouterOutput:
    return RouterOutput(
        message_category="unclear",
        owner_department=None,
        confidence="low",
        needs_clarification=True,
        clarification_question="Is this an employee or customer account?",
        platform_answer=None,
        request_type=None,
        short_summary=None,
        routing_reason="The account context is ambiguous.",
        unsupported_reason=None,
        is_capability_gap=False,
    )


class FakeClient:
    clarification_maximum = 3

    def __init__(self, result: RouterOutput) -> None:
        self.result = result

    async def classify(self, *args, **kwargs) -> RouterOutput:
        return self.result


def runtime(
    output: RouterOutput,
    *,
    department_id=None,
    active=True,
) -> SimpleNamespace:
    departments = {}
    if output.owner_department is not None and department_id is not False:
        departments[output.owner_department] = DepartmentRuntimeContext(
            department_id=department_id or uuid4(),
            is_active=active,
        )
    return SimpleNamespace(
        context=WorkflowRuntimeContext(
            router_client=FakeClient(output),
            departments=departments,
        )
    )


def test_router_assigns_tenant_department_and_trusted_fields() -> None:
    current = state()
    department_id = uuid4()

    update = asyncio.run(router_node(current, runtime(routed(), department_id=department_id)))
    result = apply_state_update(current, update)

    assert result.request.owner_department_id == department_id
    assert result.request.active_department_id == department_id
    assert result.request.company_id == current.request.company_id
    assert result.request.requester_user_id == current.request.requester_user_id
    assert result.request.request_type == "account_access_request"


def test_clarification_is_persistable_and_increments_once() -> None:
    current = state()

    update = asyncio.run(router_node(current, runtime(unclear())))
    result = apply_state_update(current, update)

    assert result.routing.clarification_count == 1
    assert result.routing.routing_pending is True
    assert result.routing.latest_question == "Is this an employee or customer account?"
    assert result.request.current_stage == "awaiting_router_clarification"


def test_clarification_maximum_is_enforced_in_graph() -> None:
    current = state()
    current.routing.clarification_count = 3

    with pytest.raises(RouterOutputError, match="clarification limit"):
        asyncio.run(router_node(current, runtime(unclear())))


@pytest.mark.parametrize("active", [False])
def test_inactive_tenant_department_is_rejected(active: bool) -> None:
    with pytest.raises(RouterDepartmentUnavailableError):
        asyncio.run(router_node(state(), runtime(routed(), active=active)))


def test_unavailable_tenant_department_is_rejected() -> None:
    with pytest.raises(RouterDepartmentUnavailableError):
        asyncio.run(router_node(state(), runtime(routed(), department_id=False)))


def test_existing_owner_cannot_be_replaced() -> None:
    current = state()
    current.request.owner_department_id = uuid4()

    with pytest.raises(RouterOwnerConflictError):
        asyncio.run(router_node(current, runtime(routed(), department_id=uuid4())))
