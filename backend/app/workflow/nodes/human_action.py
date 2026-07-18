from typing import NoReturn

from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def inactive_human_action_node(_: WorkflowState) -> NoReturn:
    raise InactiveWorkflowNodeError("Human-action logic is not active in Step 9")
