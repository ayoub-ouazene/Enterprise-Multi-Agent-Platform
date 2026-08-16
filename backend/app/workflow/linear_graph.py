"""Compiled linear graph — drop-in replacement for LangGraph compiled graph.

Implements the same ``astream()`` interface but executes nodes sequentially
with simple explicit routing instead of LangGraph's framework.
"""

from __future__ import annotations

import logging
from typing import Any

from app.workflow.state import WorkflowState, WorkflowRuntimeContext

logger = logging.getLogger(__name__)


class CompiledLinearGraph:
    """Match LangGraph compiled graph interface for astream."""

    async def astream(
        self,
        state: WorkflowState,
        *,
        context: WorkflowRuntimeContext,
        stream_mode: str = "updates",
        version: str = "v2",
    ):
        """Yield updates after each step until terminal."""
        current = state
        node_name = "initialize"
        max_steps = 30
        steps = 0

        while node_name != "__end__" and steps < max_steps:
            steps += 1
            logger.debug("linear_step node=%s step=%d", node_name, steps)

            try:
                if node_name == "initialize":
                    from app.workflow.nodes.start import initialize_node
                    updates = initialize_node(current)
                elif node_name == "router":
                    from app.workflow.nodes.router import router_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        router_client=context.router_client,
                        departments=context.departments,
                        preclassified_output=context.preclassified_output,
                    )
                    updates = await router_node(current, runtime)
                elif node_name == "department_execution":
                    from app.workflow.nodes.department import department_execution_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        department_execution_service=context.department_execution_service,
                        precomputed_department_result=context.precomputed_department_result,
                    )
                    updates = await department_execution_node(current, runtime)
                elif node_name == "tool":
                    from app.workflow.nodes.tool import department_tool_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        department_execution_service=context.department_execution_service,
                    )
                    updates = await department_tool_node(current, runtime)
                elif node_name == "collaboration_receiver":
                    from app.workflow.nodes.collaboration import collaboration_receiver_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        department_execution_service=context.department_execution_service,
                        collaboration_service=context.collaboration_service,
                    )
                    updates = await collaboration_receiver_node(current, runtime)
                elif node_name == "collaboration_return":
                    from app.workflow.nodes.collaboration import collaboration_return_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        department_execution_service=context.department_execution_service,
                        collaboration_service=context.collaboration_service,
                    )
                    updates = await collaboration_return_node(current, runtime)
                elif node_name == "reviewer":
                    from app.workflow.nodes.reviewer import reviewer_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(review_service=context.review_service)
                    updates = await reviewer_node(current, runtime)
                elif node_name == "human_action":
                    from app.workflow.nodes.human_action import customer_support_human_action_node
                    from app.workflow.runtime_adapter import RuntimeContext
                    runtime = RuntimeContext(
                        department_execution_service=context.department_execution_service,
                    )
                    updates = await customer_support_human_action_node(current, runtime)
                elif node_name == "completion":
                    from app.workflow.nodes.completion import completion_node
                    updates = completion_node(current)
                elif node_name == "failure":
                    from app.workflow.nodes.failure import terminal_failure_node
                    updates = terminal_failure_node(current)
                else:
                    logger.error("Unknown node %s", node_name)
                    break

                yield {"type": "updates", "data": {node_name: updates}}

            except Exception as exc:
                logger.exception("Node %s failed: %s", node_name, exc)
                raise

            # Determine next node
            node_name = self._route_next(node_name, current)

        if steps >= max_steps:
            logger.error("Max linear steps reached")

    async def ainvoke(self, state: WorkflowState, **kwargs: Any) -> WorkflowState:
        """Backward-compat: single-shot invocation that returns final state."""
        async for _ in self.astream(state, **kwargs):
            pass
        return state

    @staticmethod
    def _route_next(current_node: str, state: WorkflowState) -> str:
        from langgraph.graph import END
        from app.workflow.routing import (
            route_next_skeleton_node,
            route_after_router,
            route_after_department,
            route_after_collaboration_receiver,
            route_after_collaboration_return,
            route_after_collaboration_start,
            route_after_reviewer,
        )

        if current_node == "initialize":
            return route_next_skeleton_node(state)
        if current_node == "router":
            return route_after_router(state)
        if current_node == "department_stage_start":
            return "department_execution"
        if current_node == "department_execution":
            result = route_after_department(state)
            if result == END:
                return "__end__"
            return result
        if current_node == "tool":
            return "department_execution"
        if current_node == "collaboration_start":
            return route_after_collaboration_start(state)
        if current_node == "collaboration_receiver":
            return route_after_collaboration_receiver(state)
        if current_node == "collaboration_return":
            return route_after_collaboration_return(state)
        if current_node == "reviewer":
            return route_after_reviewer(state)
        if current_node == "human_action":
            return END
        if current_node == "failure":
            return "completion"
        if current_node == "completion":
            return END
        return END
