from typing import Any

from langgraph.graph import END, START, StateGraph

from app.workflow.nodes.completion import completion_node
from app.workflow.nodes.collaboration import (
    collaboration_receiver_node,
    collaboration_return_node,
    collaboration_start_node,
)
from app.workflow.nodes.department import (
    department_stage_start_node,
    department_execution_node,
)
from app.workflow.nodes.failure import terminal_failure_node
from app.workflow.nodes.human_action import customer_support_human_action_node
from app.workflow.nodes.reviewer import inactive_reviewer_node
from app.workflow.nodes.router import router_node
from app.workflow.nodes.start import initialize_node
from app.workflow.nodes.tool import department_tool_node
from app.workflow.routing import (
    route_after_department,
    route_after_router,
    route_next_skeleton_node,
    route_after_collaboration_receiver,
    route_after_collaboration_return,
    route_after_collaboration_start,
)
from app.workflow.state import WorkflowRuntimeContext, WorkflowState


def build_workflow_graph() -> Any:
    builder = StateGraph(WorkflowState, context_schema=WorkflowRuntimeContext)
    builder.add_node("initialize", initialize_node)
    builder.add_node("router", router_node)
    builder.add_node("department_stage_start", department_stage_start_node)
    builder.add_node("department_execution", department_execution_node)
    builder.add_node("tool", department_tool_node)
    builder.add_node("collaboration_start", collaboration_start_node)
    builder.add_node("collaboration_receiver", collaboration_receiver_node)
    builder.add_node("collaboration_return", collaboration_return_node)
    builder.add_node("reviewer", inactive_reviewer_node)
    builder.add_node("human_action", customer_support_human_action_node)
    builder.add_node("failure", terminal_failure_node)
    builder.add_node("completion", completion_node)

    builder.add_edge(START, "initialize")
    builder.add_conditional_edges(
        "initialize",
        route_next_skeleton_node,
        {
            "router": "router",
            "department_stage_start": "department_stage_start",
            "department_execution": "department_execution",
            "collaboration_start": "collaboration_start",
            "collaboration_receiver": "collaboration_receiver",
            "collaboration_return": "collaboration_return",
            "completion": "completion",
            END: END,
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
    builder.add_edge("department_stage_start", "department_execution")
    builder.add_conditional_edges(
        "department_execution",
        route_after_department,
        {
            "department_execution": "department_execution",
            "tool": "tool",
            "collaboration": "collaboration_start",
            "reviewer": "reviewer",
            "human_action": "human_action",
            "completion": "completion",
            "failure": "failure",
            END: END,
        },
    )
    builder.add_edge("tool", "department_execution")
    builder.add_conditional_edges(
        "collaboration_start",
        route_after_collaboration_start,
        {
            "collaboration_receiver": "collaboration_receiver",
            "collaboration_return": "collaboration_return",
        },
    )
    builder.add_conditional_edges(
        "collaboration_receiver",
        route_after_collaboration_receiver,
        {
            "collaboration_start": "collaboration_start",
            "collaboration_return": "collaboration_return",
            END: END,
        },
    )
    builder.add_conditional_edges(
        "collaboration_return",
        route_after_collaboration_return,
        {
            "collaboration_receiver": "collaboration_receiver",
            "department_execution": "department_execution",
        },
    )
    builder.add_edge("completion", END)
    return builder.compile()


workflow_graph = build_workflow_graph()
