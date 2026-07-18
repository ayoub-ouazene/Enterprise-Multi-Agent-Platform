from typing import NoReturn

from app.workflow.exceptions import InactiveWorkflowNodeError
from app.workflow.state import WorkflowState


def inactive_reviewer_node(_: WorkflowState) -> NoReturn:
    raise InactiveWorkflowNodeError("Reviewer logic is not active in Step 9")
