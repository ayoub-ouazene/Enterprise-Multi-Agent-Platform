from typing import NoReturn

from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def inactive_collaboration_node(_: WorkflowState) -> NoReturn:
    raise InactiveWorkflowNodeError(
        "Cross-department execution is not active in Step 11"
    )
