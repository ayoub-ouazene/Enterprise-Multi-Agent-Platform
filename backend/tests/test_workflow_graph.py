import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.core.enums import DepartmentType
from app.departments.contracts import DepartmentExecutionResult
from app.departments.execution import DepartmentExecutionService
from app.requests.enums import RequestStatus
from app.workflow.graph import build_workflow_graph
from app.workflow.router_output import RouterOutput
from app.workflow.state import (
    COMPLETED_STEP,
    DEPARTMENT_COMPLETED_STEP,
    DepartmentRuntimeContext,
    ROUTED_STEP,
    WorkflowRuntimeContext,
    WorkflowState,
    build_initial_workflow_state,
)


class FakeRouterClient:
    clarification_maximum = 3

    async def classify(self, *args, **kwargs) -> RouterOutput:
        return RouterOutput(
            message_category="business_request",
            owner_department="it",
            confidence="high",
            needs_clarification=False,
            clarification_question=None,
            platform_answer=None,
            request_type="hardware_request",
            short_summary="Employee requests a laptop.",
            routing_reason="Hardware requests belong to IT.",
            unsupported_reason=None,
            is_capability_gap=False,
        )


class FakeDepartmentExecutionService:
    async def execute(self, state):
        result = DepartmentExecutionResult(
            department_type="it",
            status="completed",
            decision="placeholder_execution_completed",
            reason="IT execution foundation validated.",
            user_message="The IT placeholder completed its foundation check.",
            current_stage="it_placeholder_completed",
            completed_step="it_placeholder_completed",
            next_action="complete_request",
            is_terminal=True,
            safe_event_title="IT stage completed",
            safe_event_message="IT execution foundation validated.",
        )
        return DepartmentExecutionService._safe_state_update(state, result)


def initial_state() -> WorkflowState:
    return build_initial_workflow_state(
        SimpleNamespace(
            id=uuid4(),
            company_id=uuid4(),
            requester_user_id=uuid4(),
            requester_employee_id=None,
            request_type="test_it_request",
            owner_department_id=None,
            active_department_id=None,
            status=RequestStatus.CREATED,
            current_stage="request_received",
            summary="Test the deterministic workflow.",
        )
    )


def test_graph_compiles() -> None:
    graph = build_workflow_graph()

    assert graph is not None
    assert "router" in graph.get_graph().nodes


def test_deterministic_graph_reaches_completion() -> None:
    state = initial_state()
    department_id = uuid4()

    result = asyncio.run(
        build_workflow_graph().ainvoke(
            state,
            context=WorkflowRuntimeContext(
                router_client=FakeRouterClient(),
                departments={
                    DepartmentType.IT: DepartmentRuntimeContext(
                        department_id=department_id,
                        is_active=True,
                    )
                },
                department_execution_service=FakeDepartmentExecutionService(),
            ),
        )
    )
    completed = WorkflowState.model_validate(result)

    assert completed.request.status == RequestStatus.COMPLETED
    assert completed.request.owner_department_id == department_id
    assert ROUTED_STEP in completed.planning.completed_steps
    assert DEPARTMENT_COMPLETED_STEP in completed.planning.completed_steps
    assert COMPLETED_STEP in completed.planning.completed_steps
    assert len(completed.planning.completed_steps) == len(
        set(completed.planning.completed_steps)
    )


def test_graph_routes_any_valid_request_type_from_structured_output() -> None:
    state = initial_state()
    state.request.request_type = "real_production_request"

    department_id = uuid4()
    result = asyncio.run(
        build_workflow_graph().ainvoke(
            state,
            context=WorkflowRuntimeContext(
                router_client=FakeRouterClient(),
                departments={
                    DepartmentType.IT: DepartmentRuntimeContext(
                        department_id=department_id,
                        is_active=True,
                    )
                },
                department_execution_service=FakeDepartmentExecutionService(),
            ),
        )
    )

    completed = WorkflowState.model_validate(result)
    assert completed.request.request_type == "hardware_request"
    assert completed.request.owner_department_id == department_id
