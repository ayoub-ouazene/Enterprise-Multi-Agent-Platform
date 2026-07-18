from typing import Any

from langgraph.runtime import Runtime

from app.workflow.exceptions import (
    RouterDepartmentUnavailableError,
    RouterOwnerConflictError,
)
from app.llm.exceptions import RouterOutputError
from app.workflow.router_output import RouterMessageCategory
from app.workflow.state import (
    ROUTED_STEP,
    WorkflowRuntimeContext,
    WorkflowState,
    add_completed_step,
)


async def router_node(
    state: WorkflowState,
    runtime: Runtime[WorkflowRuntimeContext],
) -> dict[str, Any]:
    """Invoke the validated Router and apply only trusted routing fields."""

    if ROUTED_STEP in state.planning.completed_steps:
        return {}
    output = runtime.context.preclassified_output
    if output is None:
        output = await runtime.context.router_client.classify(
            state.request.summary,
            clarification_count=state.routing.clarification_count,
            latest_question=state.routing.latest_question,
            latest_answer=state.routing.latest_answer,
        )

    routing = state.routing.model_copy(
        update={
            "message_category": output.message_category,
            "selected_department": output.owner_department,
            "confidence": output.confidence,
            "needs_clarification": output.needs_clarification,
            "request_type": output.request_type,
            "short_summary": output.short_summary,
            "routing_reason": output.routing_reason,
            "unsupported_reason": output.unsupported_reason,
            "is_capability_gap": output.is_capability_gap,
            "platform_answer": output.platform_answer,
        }
    )

    if output.message_category == RouterMessageCategory.UNCLEAR:
        if (
            state.routing.clarification_count
            >= runtime.context.router_client.clarification_maximum
        ):
            raise RouterOutputError("The Router exceeded the clarification limit")
        routing = routing.model_copy(
            update={
                "clarification_count": state.routing.clarification_count + 1,
                "latest_question": output.clarification_question,
                "routing_pending": True,
            }
        )
        request = state.request.model_copy(
            update={"current_stage": "awaiting_router_clarification"}
        )
        planning = state.planning.model_copy(update={"current_step": "router"})
        return {"request": request, "routing": routing, "planning": planning}

    if output.message_category in {
        RouterMessageCategory.PLATFORM_QUESTION,
        RouterMessageCategory.UNSUPPORTED,
    }:
        routing = routing.model_copy(
            update={
                "latest_question": None,
                "routing_pending": False,
            }
        )
        stage = (
            "platform_response"
            if output.message_category == RouterMessageCategory.PLATFORM_QUESTION
            else "unsupported"
        )
        request = state.request.model_copy(update={"current_stage": stage})
        planning = add_completed_step(state, ROUTED_STEP).model_copy(
            update={"current_step": "completion"}
        )
        return {"request": request, "routing": routing, "planning": planning}

    department_type = output.owner_department
    if department_type is None:
        raise RouterDepartmentUnavailableError("Router selected no department")
    department = runtime.context.departments.get(department_type)
    if department is None or not department.is_active:
        raise RouterDepartmentUnavailableError(
            "The selected tenant department is unavailable"
        )
    if (
        state.request.owner_department_id is not None
        and state.request.owner_department_id != department.department_id
    ):
        raise RouterOwnerConflictError("The request owner cannot be replaced")

    request = state.request.model_copy(
        update={
            "owner_department_id": department.department_id,
            "active_department_id": department.department_id,
            "request_type": output.request_type,
            "summary": output.short_summary,
            "current_stage": "request_routed",
        }
    )
    routing = routing.model_copy(
        update={
            "latest_question": None,
            "routing_pending": False,
        }
    )
    planning = add_completed_step(state, ROUTED_STEP).model_copy(
        update={"current_step": "placeholder_department_started"}
    )
    return {"request": request, "routing": routing, "planning": planning}
