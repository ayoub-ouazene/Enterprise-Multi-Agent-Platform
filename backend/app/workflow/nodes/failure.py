from typing import NoReturn

from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def inactive_failure_node(_: WorkflowState) -> NoReturn:
    raise InactiveWorkflowNodeError(
        "Graph failures are handled by WorkflowService in Step 9"
    )
