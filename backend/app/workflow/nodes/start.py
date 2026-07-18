from typing import Any

from app.workflow.state import (
    INITIALIZED_STEP,
    WorkflowState,
    add_completed_step,
)


def initialize_node(state: WorkflowState) -> dict[str, Any]:
    """Validate graph input and mark initialization once."""

    if INITIALIZED_STEP in state.planning.completed_steps:
        return {}
    planning = add_completed_step(state, INITIALIZED_STEP).model_copy(
        update={"current_step": "placeholder_router"}
    )
    return {"planning": planning}
