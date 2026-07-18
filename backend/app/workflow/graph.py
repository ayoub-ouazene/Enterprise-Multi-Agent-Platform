from typing import Any

from langgraph.graph import END, START, StateGraph

from app.workflow.nodes.completion import completion_node
from app.workflow.nodes.department import (
    department_stage_start_node,
    placeholder_department_node,
)
from app.workflow.nodes.router import router_node
from app.workflow.nodes.start import initialize_node
from app.workflow.routing import route_after_router, route_next_skeleton_node
from app.workflow.state import WorkflowRuntimeContext, WorkflowState


def build_workflow_graph() -> Any:
    builder = StateGraph(WorkflowState, context_schema=WorkflowRuntimeContext)
    builder.add_node("initialize", initialize_node)
    builder.add_node("router", router_node)
    builder.add_node("department_stage_start", department_stage_start_node)
    builder.add_node("placeholder_department", placeholder_department_node)
    builder.add_node("completion", completion_node)

    builder.add_edge(START, "initialize")
    builder.add_conditional_edges(
        "initialize",
        route_next_skeleton_node,
        {
            "router": "router",
            "department_stage_start": "department_stage_start",
            "placeholder_department": "placeholder_department",
            "completion": "completion",
        },
    )
    builder.add_conditional_edges(
        "router",
        route_after_router,
        {
            "department_stage_start": "department_stage_start",
            "completion": "completion",
            END: END,
        },
    )
    builder.add_edge("department_stage_start", "placeholder_department")
    builder.add_edge("placeholder_department", "completion")
    builder.add_edge("completion", END)
    return builder.compile()


workflow_graph = build_workflow_graph()
