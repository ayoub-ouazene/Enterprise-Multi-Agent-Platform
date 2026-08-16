"""Router step: classify the user message and decide what to do next.

Uses the unified ``GroqLLMClient`` instead of the old ``GroqRouterClient``.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.enums import DepartmentType
from app.llm.client import GroqLLMClient
from app.llm.exceptions import RouterProviderError, RouterOutputError, RouterConfigurationError
from app.requests.enums import RequestStatus
from app.workflow.prompts.router import ROUTER_SYSTEM_PROMPT, build_router_user_message
from app.workflow.router_output import RouterMessageCategory, RouterOutput, RouterConfidence
from app.workflow.simple_state import RoutingStatus, WorkflowState, ExecutionStatus

logger = logging.getLogger(__name__)


class RouterStep:
    def __init__(self, llm_client: GroqLLMClient) -> None:
        self.llm = llm_client

    async def run(self, state: WorkflowState) -> WorkflowState:
        message = state.request.summary
        if state.routing.latest_answer:
            message = state.routing.latest_answer

        try:
            raw = await self.llm.generate(
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_router_user_message(
                            message=message,
                            clarification_count=state.routing.clarification_count,
                            clarification_maximum=3,
                            latest_question=state.routing.latest_question,
                            latest_answer=state.routing.latest_answer,
                        ),
                    },
                ],
                model=self.llm.settings.groq_model_router,
                response_schema=RouterOutput,
                role_name="router",
                on_provider_error=RouterProviderError,
                on_output_error=RouterOutputError,
            )
        except RouterConfigurationError:
            raise
        except (RouterProviderError, RouterOutputError):
            raise

        output = RouterOutput.model_validate(raw)
        logger.info(
            "router_decision category=%s department=%s confidence=%s request_id=%s",
            output.message_category,
            output.owner_department,
            output.confidence,
            state.request.request_id,
        )

        # Update routing section
        routing = state.routing
        routing = routing.replace(
            status=RoutingStatus.DONE,
            message_category=output.message_category,
            selected_department=output.owner_department,
            confidence=output.confidence.value if output.confidence else None,
            needs_clarification=output.needs_clarification,
            clarification_count=routing.clarification_count + (1 if output.needs_clarification else 0),
            latest_question=output.clarification_question,
            request_type=output.request_type,
            short_summary=output.short_summary,
            routing_reason=output.routing_reason,
            unsupported_reason=output.unsupported_reason,
            is_capability_gap=output.is_capability_gap,
            platform_answer=output.platform_answer,
        )
        state = state.with_routing(**routing.__dict__)

        # Platform question -> immediate completion
        if output.message_category == RouterMessageCategory.PLATFORM_QUESTION:
            state = state.with_execution(status=ExecutionStatus.COMPLETED)
            state = state.with_result(
                final_response=output.platform_answer or "Platform guidance is unavailable.",
                decision="completed",
            )
            state = state.with_request(
                status=RequestStatus.COMPLETED,
                current_stage="completed",
            )
            return state

        # Unclear -> needs clarification (pause)
        if output.message_category == RouterMessageCategory.UNCLEAR:
            state = state.with_execution(status=ExecutionStatus.NEEDS_HUMAN)
            state = state.with_human_action(
                required=True,
                action_type="clarification",
                status="waiting_for_user",
            )
            state = state.with_request(
                status=RequestStatus.WAITING_FOR_HUMAN_ACTION,
                current_stage="needs_clarification",
            )
            return state

        # Unsupported -> fail with capability gap
        if output.message_category == RouterMessageCategory.UNSUPPORTED:
            state = state.with_execution(status=ExecutionStatus.COMPLETED)
            state = state.with_failure(
                has_failure=True,
                failure_type="capability_gap",
                safe_message=output.unsupported_reason or "This operation is not currently supported.",
                terminal=True,
            )
            state = state.with_result(
                final_response=output.unsupported_reason or "This operation is not currently supported.",
                decision="unsupported",
            )
            state = state.with_request(
                status=RequestStatus.FAILED,
                current_stage="failed",
            )
            return state

        # Routed to a department -> prepare for department execution
        department = output.owner_department
        state = state.with_request(
            owner_department_id=None,  # Will be resolved by department step
            owner_department_type=department,
            active_department_type=department,
            status=RequestStatus.PROCESSING,
            current_stage=f"{department.value}_analysis",
            request_type=output.request_type or f"{department.value}_request",
        )
        state = state.with_execution(status=ExecutionStatus.RUNNING)
        state = state.with_planning(
            current_step="department_execution",
            pending_steps=["department_execution", "completion"],
        )
        return state

    @staticmethod
    def _build_department_state(state: WorkflowState, output: RouterOutput) -> WorkflowState:
        """Set request state for department execution."""
        dept = output.owner_department
        return (
            state.with_request(
                owner_department_type=dept,
                active_department_type=dept,
                status=RequestStatus.PROCESSING,
                current_stage=f"{dept.value}_analysis",
                request_type=output.request_type or f"{dept.value}_request",
            )
            .with_execution(status=ExecutionStatus.RUNNING)
            .with_planning(
                current_step="department_execution",
                pending_steps=["department_execution", "completion"],
            )
        )


async def router_step(state: WorkflowState) -> WorkflowState:
    """Entry-point used by the engine."""
    from app.core.config import get_settings
    settings = get_settings()
    client = GroqLLMClient(settings)
    return await RouterStep(client).run(state)
